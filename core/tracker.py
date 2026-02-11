"""
ByteTrack tracker module
Handles multi-object tracking
"""
import numpy as np
from typing import List, Optional, Dict
from dataclasses import dataclass, field

from config import TrackerConfig
from .detector import Detection


@dataclass
class Track:
    """Tracked object data class"""
    track_id: int
    detection: Detection
    age: int = 0  # Frames tracked
    hits: int = 0  # Hit count
    time_since_update: int = 0  # Frames since last update
    
    @property
    def bbox(self) -> np.ndarray:
        return self.detection.bbox
    
    @property
    def keypoints(self) -> np.ndarray:
        return self.detection.keypoints


class KalmanBoxTracker:
    """
    Single object bounding box tracker using Kalman filter
    """
    count = 0
    
    def __init__(self, detection: Detection):
        """
        Initialize tracker
        """
        from filterpy.kalman import KalmanFilter
        
        # State vector: [x_center, y_center, area, aspect_ratio, vx, vy, va]
        self.kf = KalmanFilter(dim_x=7, dim_z=4)
        
        # State transition matrix
        self.kf.F = np.array([
            [1, 0, 0, 0, 1, 0, 0],
            [0, 1, 0, 0, 0, 1, 0],
            [0, 0, 1, 0, 0, 0, 1],
            [0, 0, 0, 1, 0, 0, 0],
            [0, 0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 0, 1]
        ])
        
        # Observation matrix
        self.kf.H = np.array([
            [1, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0, 0],
            [0, 0, 0, 1, 0, 0, 0]
        ])
        
        # Initialize state
        bbox = detection.bbox
        self.kf.x[:4] = self._bbox_to_z(bbox).reshape((4, 1))
        
        # Noise covariance
        self.kf.R[2:, 2:] *= 10.0
        self.kf.P[4:, 4:] *= 1000.0
        self.kf.P *= 10.0
        self.kf.Q[-1, -1] *= 0.01
        self.kf.Q[4:, 4:] *= 0.01
        
        self.time_since_update = 0
        self.id = KalmanBoxTracker.count
        KalmanBoxTracker.count += 1
        self.hits = 0
        self.age = 0
        self.detection = detection
        
    def _bbox_to_z(self, bbox: np.ndarray) -> np.ndarray:
        """Convert bounding box to observation vector [x_c, y_c, area, ratio]"""
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x_c = bbox[0] + w / 2
        y_c = bbox[1] + h / 2
        area = w * h
        ratio = w / (h + 1e-6)
        return np.array([x_c, y_c, area, ratio])
    
    def _z_to_bbox(self, z: np.ndarray) -> np.ndarray:
        """Convert observation vector to bounding box"""
        w = np.sqrt(z[2] * z[3])
        h = z[2] / (w + 1e-6)
        x1 = z[0] - w / 2
        y1 = z[1] - h / 2
        x2 = z[0] + w / 2
        y2 = z[1] + h / 2
        return np.array([x1, y1, x2, y2])
    
    def update(self, detection: Detection):
        """Update tracker state"""
        self.time_since_update = 0
        self.hits += 1
        self.detection = detection
        self.kf.update(self._bbox_to_z(detection.bbox))
    
    def predict(self) -> np.ndarray:
        """Predict next frame bounding box"""
        if self.kf.x[6] + self.kf.x[2] <= 0:
            self.kf.x[6] *= 0.0
        self.kf.predict()
        self.age += 1
        self.time_since_update += 1
        return self._z_to_bbox(self.kf.x[:4].flatten())
    
    def get_state(self) -> np.ndarray:
        """Get current bounding box state"""
        return self._z_to_bbox(self.kf.x[:4].flatten())


class ByteTracker:
    """ByteTrack multi-object tracker"""
    
    def __init__(self, config: TrackerConfig):
        """
        Initialize tracker
        
        Args:
            config: Tracker configuration
        """
        self.config = config
        self.trackers: List[KalmanBoxTracker] = []
        self.frame_count = 0
        
    def _iou(self, bbox1: np.ndarray, bbox2: np.ndarray) -> float:
        """Compute IOU of two bounding boxes"""
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])
        
        inter_area = max(0, x2 - x1) * max(0, y2 - y1)
        
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        
        union_area = area1 + area2 - inter_area
        
        return inter_area / (union_area + 1e-6)
    
    def _iou_matrix(self, dets: List[Detection], trackers: List[KalmanBoxTracker]) -> np.ndarray:
        """Compute IOU matrix between detections and trackers"""
        if len(dets) == 0 or len(trackers) == 0:
            return np.zeros((len(dets), len(trackers)))
        
        iou_matrix = np.zeros((len(dets), len(trackers)))
        for d, det in enumerate(dets):
            for t, trk in enumerate(trackers):
                iou_matrix[d, t] = self._iou(det.bbox, trk.get_state())
        
        return iou_matrix
    
    def _linear_assignment(self, cost_matrix: np.ndarray, thresh: float):
        """Linear assignment"""
        from scipy.optimize import linear_sum_assignment
        
        if cost_matrix.size == 0:
            return np.empty((0, 2), dtype=int), list(range(cost_matrix.shape[0])), list(range(cost_matrix.shape[1]))
        
        # Convert to cost matrix (1 - IOU)
        cost = 1 - cost_matrix
        row_indices, col_indices = linear_sum_assignment(cost)
        
        matches = []
        unmatched_dets = list(range(cost_matrix.shape[0]))
        unmatched_trks = list(range(cost_matrix.shape[1]))
        
        for row, col in zip(row_indices, col_indices):
            if cost_matrix[row, col] >= thresh:
                matches.append([row, col])
                unmatched_dets.remove(row)
                unmatched_trks.remove(col)
        
        return np.array(matches).reshape(-1, 2), unmatched_dets, unmatched_trks
    
    def update(self, detections: List[Detection]) -> List[Track]:
        """
        Update tracker
        
        Args:
            detections: Detection results for current frame
            
        Returns:
            List of tracking results
        """
        self.frame_count += 1
        
        # Predict positions of existing trackers
        for trk in self.trackers:
            trk.predict()
        
        # Filter low-confidence detections
        high_conf_dets = [d for d in detections if d.confidence >= self.config.track_thresh]
        low_conf_dets = [d for d in detections if d.confidence < self.config.track_thresh]
        
        # First association: high-confidence detections with trackers
        iou_matrix = self._iou_matrix(high_conf_dets, self.trackers)
        matches, unmatched_dets, unmatched_trks = self._linear_assignment(
            iou_matrix, self.config.match_thresh
        )
        # Ensure always a list (prevent tuple remove failure)
        unmatched_dets = list(unmatched_dets)
        unmatched_trks = list(unmatched_trks)
        
        # Update matched trackers
        for m in matches:
            if m[1] < len(self.trackers):
                self.trackers[m[1]].update(high_conf_dets[m[0]])
        
        # Second association: low-confidence detections with unmatched trackers
        if len(low_conf_dets) > 0 and len(unmatched_trks) > 0:
            try:
                unmatched_trks_snapshot = list(unmatched_trks)
                remaining_trackers = [self.trackers[i] for i in unmatched_trks_snapshot if i < len(self.trackers)]
                if len(remaining_trackers) > 0:
                    iou_matrix2 = self._iou_matrix(low_conf_dets, remaining_trackers)
                    matches2, _, _ = self._linear_assignment(iou_matrix2, 0.5)

                    matched_orig_indices = []
                    for m in matches2:
                        if m[1] < len(unmatched_trks_snapshot):
                            orig_idx = unmatched_trks_snapshot[m[1]]
                            if orig_idx < len(self.trackers):
                                self.trackers[orig_idx].update(low_conf_dets[m[0]])
                                matched_orig_indices.append(orig_idx)
                    for idx in matched_orig_indices:
                        if idx in unmatched_trks:
                            unmatched_trks.remove(idx)
            except (IndexError, ValueError) as e:
                pass  # Skip second association errors without affecting main flow
        
        # Create new trackers for unmatched high-confidence detections
        for i in unmatched_dets:
            det = high_conf_dets[i]
            if det.area >= self.config.min_box_area:
                self.trackers.append(KalmanBoxTracker(det))
        
        # Clean up expired trackers
        tracks = []
        i = len(self.trackers) - 1
        while i >= 0:
            trk = self.trackers[i]
            if trk.time_since_update < 1:
                track = Track(
                    track_id=trk.id,
                    detection=trk.detection,
                    age=trk.age,
                    hits=trk.hits,
                    time_since_update=trk.time_since_update
                )
                tracks.append(track)
            
            if trk.time_since_update > self.config.track_buffer:
                self.trackers.pop(i)
            i -= 1
        
        return tracks
    
    def reset(self):
        """Reset tracker"""
        self.trackers = []
        self.frame_count = 0
        KalmanBoxTracker.count = 0
