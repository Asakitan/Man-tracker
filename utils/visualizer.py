"""Visualization module."""
import cv2
import numpy as np
from typing import List, Tuple, Optional

from config import VisualizationConfig, SkeletonPoint
from core import Track


# COCO skeleton connections
SKELETON_CONNECTIONS = [
    (SkeletonPoint.NOSE, SkeletonPoint.LEFT_EYE),
    (SkeletonPoint.NOSE, SkeletonPoint.RIGHT_EYE),
    (SkeletonPoint.LEFT_EYE, SkeletonPoint.LEFT_EAR),
    (SkeletonPoint.RIGHT_EYE, SkeletonPoint.RIGHT_EAR),
    (SkeletonPoint.NOSE, SkeletonPoint.LEFT_SHOULDER),
    (SkeletonPoint.NOSE, SkeletonPoint.RIGHT_SHOULDER),
    (SkeletonPoint.LEFT_SHOULDER, SkeletonPoint.RIGHT_SHOULDER),
    (SkeletonPoint.LEFT_SHOULDER, SkeletonPoint.LEFT_ELBOW),
    (SkeletonPoint.RIGHT_SHOULDER, SkeletonPoint.RIGHT_ELBOW),
    (SkeletonPoint.LEFT_ELBOW, SkeletonPoint.LEFT_WRIST),
    (SkeletonPoint.RIGHT_ELBOW, SkeletonPoint.RIGHT_WRIST),
    (SkeletonPoint.LEFT_SHOULDER, SkeletonPoint.LEFT_HIP),
    (SkeletonPoint.RIGHT_SHOULDER, SkeletonPoint.RIGHT_HIP),
    (SkeletonPoint.LEFT_HIP, SkeletonPoint.RIGHT_HIP),
    (SkeletonPoint.LEFT_HIP, SkeletonPoint.LEFT_KNEE),
    (SkeletonPoint.RIGHT_HIP, SkeletonPoint.RIGHT_KNEE),
    (SkeletonPoint.LEFT_KNEE, SkeletonPoint.LEFT_ANKLE),
    (SkeletonPoint.RIGHT_KNEE, SkeletonPoint.RIGHT_ANKLE),
]


class Visualizer:
    """Visualizer."""
    
    def __init__(self, config: VisualizationConfig):
        """Initialize with the given VisualizationConfig."""
        self.config = config
    
    def draw_skeleton(
        self, 
        frame: np.ndarray, 
        keypoints: np.ndarray,
        color: Optional[Tuple[int, int, int]] = None,
        conf_threshold: float = 0.3
    ) -> np.ndarray:
        """Draw skeleton on frame."""
        if not self.config.draw_skeleton:
            return frame
        
        color = color or self.config.skeleton_color
        
        # Draw skeleton connections
        for connection in SKELETON_CONNECTIONS:
            pt1_idx = connection[0].value
            pt2_idx = connection[1].value
            
            pt1 = keypoints[pt1_idx]
            pt2 = keypoints[pt2_idx]
            
            # Check confidence
            if pt1[2] > conf_threshold and pt2[2] > conf_threshold:
                x1, y1 = int(pt1[0]), int(pt1[1])
                x2, y2 = int(pt2[0]), int(pt2[1])
                cv2.line(frame, (x1, y1), (x2, y2), color, self.config.line_thickness)
        
        # Draw joint points
        for i, kp in enumerate(keypoints):
            if kp[2] > conf_threshold:
                x, y = int(kp[0]), int(kp[1])
                cv2.circle(frame, (x, y), 4, color, -1)
                cv2.circle(frame, (x, y), 4, (0, 0, 0), 1)
        
        return frame
    
    def draw_bbox(
        self, 
        frame: np.ndarray, 
        bbox: np.ndarray,
        track_id: Optional[int] = None,
        color: Optional[Tuple[int, int, int]] = None
    ) -> np.ndarray:
        """Draw bounding box on frame."""
        if not self.config.draw_bbox:
            return frame
        
        color = color or self.config.bbox_color
        
        x1, y1, x2, y2 = map(int, bbox)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, self.config.line_thickness)
        
        # Draw track ID
        if track_id is not None and self.config.draw_track_id:
            label = f"ID: {track_id}"
            (text_w, text_h), _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1
            )
            cv2.rectangle(
                frame, 
                (x1, y1 - text_h - 10), 
                (x1 + text_w + 10, y1), 
                color, 
                -1
            )
            cv2.putText(
                frame, 
                label, 
                (x1 + 5, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                self.config.text_color,
                1,
                cv2.LINE_AA
            )
        
        return frame
    
    def draw_target_point(
        self, 
        frame: np.ndarray, 
        point: Tuple[float, float],
        label: str = "TARGET",
        color: Optional[Tuple[int, int, int]] = None
    ) -> np.ndarray:
        """Draw target point (crosshair for mouse-tracked keypoint)."""
        if not self.config.draw_target_point:
            return frame
        
        color = color or self.config.target_color
        x, y = int(point[0]), int(point[1])
        
        # Draw crosshair
        size = 15
        cv2.line(frame, (x - size, y), (x + size, y), color, 2)
        cv2.line(frame, (x, y - size), (x, y + size), color, 2)
        
        # Draw circle
        cv2.circle(frame, (x, y), size, color, 2)
        
        # Draw label
        cv2.putText(
            frame,
            label,
            (x + size + 5, y + 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
            cv2.LINE_AA
        )
        
        return frame
    
    def draw_info_panel(
        self,
        frame: np.ndarray,
        fps: float,
        track_count: int,
        target_id: Optional[int] = None,
        target_point: str = "",
        mouse_pos: Optional[Tuple[int, int]] = None
    ) -> np.ndarray:
        """Draw info panel overlay."""
        # Background
        panel_h = 120
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (300, panel_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        # Info text
        y_offset = 30
        line_height = 22
        
        info_lines = [
            f"FPS: {fps:.1f}",
            f"Tracks: {track_count}",
            f"Target ID: {target_id if target_id is not None else 'Auto'}",
            f"Target Point: {target_point}",
        ]
        
        if mouse_pos:
            info_lines.append(f"Mouse: ({mouse_pos[0]}, {mouse_pos[1]})")
        
        for line in info_lines:
            cv2.putText(
                frame,
                line,
                (20, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )
            y_offset += line_height
        
        return frame
    
    def draw_tracks(
        self,
        frame: np.ndarray,
        tracks: List[Track],
        target_track_id: Optional[int] = None,
        target_keypoint_idx: int = 0,
        active_target_track: Optional[Track] = None,
    ) -> np.ndarray:
        """Draw all tracked targets on frame.

        - Active target (mouse-controlled) → target_color
        - Enemy (has_red_edge) but not active target → red bbox/skeleton
        - Non-enemy (no red edge) → dim grey, still visible
        """
        NON_ENEMY_COLOR = (120, 120, 120)  # grey for friendlies / neutrals
        ENEMY_COLOR = (0, 0, 255)           # red for enemies not being targeted

        for track in tracks:
            is_active = (active_target_track is not None
                         and track.track_id == active_target_track.track_id)
            is_enemy = getattr(track.detection, 'has_red_edge', False)

            if is_active:
                bbox_color = self.config.target_color
                skeleton_color = self.config.target_color
            elif is_enemy:
                bbox_color = ENEMY_COLOR
                skeleton_color = ENEMY_COLOR
            else:
                bbox_color = NON_ENEMY_COLOR
                skeleton_color = NON_ENEMY_COLOR

            # Draw red edge debug mask overlay if enabled
            if getattr(self.config, 'draw_red_edge_debug', False):
                debug_mask = getattr(track.detection, 'debug_red_mask', None)
                debug_bbox = getattr(track.detection, '_debug_bbox', None)
                if debug_mask is not None and debug_bbox is not None:
                    # Draw only in the ROI region (more efficient)
                    x1, y1, x2, y2 = debug_bbox
                    h, w = frame.shape[:2]
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(w, x2), min(h, y2)
                    roi_h, roi_w = y2 - y1, x2 - x1
                    
                    if roi_h > 0 and roi_w > 0 and debug_mask.shape[0] == roi_h and debug_mask.shape[1] == roi_w:
                        # Create colored overlay in ROI (cyan for detected red pixels)
                        roi = frame[y1:y2, x1:x2].copy()
                        roi[debug_mask > 0] = [255, 255, 0]  # Cyan (BGR)
                        # Blend with original
                        frame[y1:y2, x1:x2] = cv2.addWeighted(roi, 0.5, frame[y1:y2, x1:x2], 0.5, 0)
                    
                    # Draw "RED EDGE" label if detected
                    if is_enemy:
                        bx1, by1, bx2, by2 = map(int, track.bbox)
                        cv2.putText(
                            frame, "RED EDGE", (bx1, by2 + 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1
                        )

            # Draw bounding box
            self.draw_bbox(frame, track.bbox, track.track_id, bbox_color)

            # Draw skeleton
            self.draw_skeleton(frame, track.keypoints, skeleton_color)

            # If active target, draw crosshair
            if is_active:
                kp = track.detection.get_keypoint(target_keypoint_idx)
                if kp:
                    self.draw_target_point(
                        frame,
                        (kp[0], kp[1]),
                        SkeletonPoint(target_keypoint_idx).name
                    )

        return frame
    
    def draw_help(self, frame: np.ndarray) -> np.ndarray:
        """Draw help overlay."""
        help_text = [
            "Controls:",
            "Q - Quit",
            "SPACE - Pause",
            "M - Toggle mouse control",
            "1-9 - Select target ID",
            "S - Change skeleton point",
        ]
        
        h, w = frame.shape[:2]
        x_start = w - 200
        y_start = 30
        
        # Background
        overlay = frame.copy()
        cv2.rectangle(overlay, (x_start - 10, 10), (w - 10, y_start + len(help_text) * 20), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        for i, text in enumerate(help_text):
            cv2.putText(
                frame,
                text,
                (x_start, y_start + i * 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (200, 200, 200),
                1,
                cv2.LINE_AA
            )
        
        return frame
