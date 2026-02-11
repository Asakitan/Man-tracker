"""
Detection module
"""
import os
import cv2
import numpy as np
from typing import Optional, List, Tuple
from dataclasses import dataclass

from config import DetectorConfig
from utils.resource_path import resource_path
from utils.model_manager import ModelManager


@dataclass
class Detection:
    bbox: np.ndarray       # [x1, y1, x2, y2]
    confidence: float
    keypoints: np.ndarray  # [17, 3] (x, y, conf)
    has_red_edge: bool = False  # True = enemy (red glow detected)
    debug_red_mask: Optional[np.ndarray] = None  # Debug: red edge mask for visualization

    @property
    def center(self) -> Tuple[float, float]:
        return (
            (self.bbox[0] + self.bbox[2]) / 2,
            (self.bbox[1] + self.bbox[3]) / 2
        )

    @property
    def area(self) -> float:
        return (self.bbox[2] - self.bbox[0]) * (self.bbox[3] - self.bbox[1])

    def get_keypoint(self, idx: int) -> Optional[Tuple[float, float, float]]:
        if idx < 0 or idx >= len(self.keypoints):
            return None
        kp = self.keypoints[idx]
        if kp[2] < 0.15:
            return None
        return (float(kp[0]), float(kp[1]), float(kp[2]))


class PoseDetector:

    def __init__(self, config: DetectorConfig):
        self.config = config
        self.model = self._load_model()

    def _resolve_device(self) -> str:
        import torch
        requested = self.config.device.lower()
        if requested == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        elif requested == "cuda" and not torch.cuda.is_available():
            device = "cpu"
        else:
            device = requested
        self.config.device = device
        return device

    def _load_model(self):
        try:
            # Dynamically import inference engine
            _pkg = __import__(''.join(chr(c) for c in [117,108,116,114,97,108,121,116,105,99,115]), fromlist=[chr(89)+chr(79)+chr(76)+chr(79)])
            _Cls = getattr(_pkg, chr(89)+chr(79)+chr(76)+chr(79))

            device = self._resolve_device()

            # Resolve model path: try configured name, resource_path, then auto-discover
            model_path = self.config.model_path
            resolved = resource_path(model_path)
            if _is_file(model_path):
                pass
            elif _is_file(resolved):
                model_path = resolved
            else:
                # Auto-discover: find any .pt file in project dir
                _proj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                _pts = [
                    f for f in os.listdir(_proj)
                    if f.endswith(".pt") and os.path.isfile(os.path.join(_proj, f))
                ]
                if _pts:
                    model_path = os.path.join(_proj, _pts[0])

            # Obfuscate model filename via ModelManager
            mgr = ModelManager.instance()
            obf_path = mgr.prepare(model_path, internal_tag=f"[model:{self.config.model_path}]")

            model = _Cls(obf_path)

            use_half = self.config.half_precision and device == "cuda"

            # Warmup
            model.predict(
                np.zeros((320, 320, 3), dtype=np.uint8),
                device=device,
                half=use_half,
                verbose=False
            )
            self._use_half = use_half
            # Internal identity tracking
            self._identity = mgr.get_identity(obf_path)
            return model
        except Exception as e:
            raise RuntimeError(f"Model load error: {e}")

    def _extract_red_glow_mask_fast(self, frame: np.ndarray) -> np.ndarray:
        """
        Fast red glow detection using only RGB comparison.
        Optimized for speed over accuracy.
        """
        # Direct RGB comparison (fastest method)
        b, g, r = frame[:, :, 0], frame[:, :, 1], frame[:, :, 2]
        
        # Red channel should dominate
        r_int = r.astype(np.int16)
        g_int = g.astype(np.int16)
        b_int = b.astype(np.int16)
        
        # Simple threshold: R > 80 and R > G+20 and R > B+20
        red_mask = (r > 80) & (r_int > g_int + 20) & (r_int > b_int + 20)
        
        return red_mask.astype(np.uint8) * 255

    def _extract_red_glow_mask(self, frame: np.ndarray) -> np.ndarray:
        """
        Extract red glow regions from the frame.
        Returns a binary mask of red glowing pixels.
        
        Red glow in games typically has:
        - High red channel relative to green/blue
        - Can appear as orange-red to deep red
        - Often has high brightness (value)
        """
        # Use fast method by default
        return self._extract_red_glow_mask_fast(frame)

    def _is_humanoid_shape(self, contour: np.ndarray, min_area: int = 100) -> bool:
        """
        Check if a contour has a roughly humanoid shape.
        
        Humanoid characteristics:
        - Roughly vertical orientation (taller than wide, or close to square)
        - Reasonable aspect ratio (0.2 to 1.5 for width/height)
        - Not too thin (like a line) or too circular
        """
        area = cv2.contourArea(contour)
        if area < min_area:
            return False
        
        # Get bounding rect
        x, y, w, h = cv2.boundingRect(contour)
        if h < 5 or w < 3:
            return False
        
        aspect = w / h
        
        # Humanoid aspect ratio: 0.15 (very thin person far away) to 1.2 (crouching/wide)
        if aspect < 0.15 or aspect > 1.5:
            return False
        
        # Check solidity (area / convex hull area) - humans aren't too sparse
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        if hull_area > 0:
            solidity = area / hull_area
            # Very low solidity means too many holes/gaps (unlikely human outline)
            if solidity < 0.15:
                return False
        
        # Check extent (area / bounding rect area)
        rect_area = w * h
        extent = area / rect_area if rect_area > 0 else 0
        
        # Human outline should fill some portion of bounding box
        # Very low extent = too sparse, very high = too blocky
        if extent < 0.1 or extent > 0.95:
            return False
        
        return True

    def _check_red_edge(self, frame: np.ndarray, bbox: np.ndarray,
                        ratio_thresh: float = 0.02, return_debug: bool = False
                        ) -> Tuple[bool, Optional[np.ndarray], Optional[Tuple[int, int, int, int]]]:
        """Check whether a bbox region contains red glow pixels.

        Fast detection: just count red pixels in the bbox region.
        
        Returns:
            (has_red_edge, debug_mask, (x1, y1, x2, y2)) if return_debug=True
            (has_red_edge, None, None) if return_debug=False
        """
        h_img, w_img = frame.shape[:2]
        x1, y1, x2, y2 = (max(0, int(v)) for v in bbox[:4])
        x2, y2 = min(x2, w_img), min(y2, h_img)
        bw, bh = x2 - x1, y2 - y1
        if bw < 4 or bh < 4:
            return (False, None, None)

        roi = frame[y1:y2, x1:x2]
        roi_h, roi_w = roi.shape[:2]
        
        if roi_h < 4 or roi_w < 4:
            return (False, None, None)

        # Fast red detection: just count pixels where R > G+20 and R > B+20
        r, g, b = roi[:, :, 2], roi[:, :, 1], roi[:, :, 0]
        r_int = r.astype(np.int16)
        g_int = g.astype(np.int16)
        b_int = b.astype(np.int16)
        
        red_mask = (r > 80) & (r_int > g_int + 20) & (r_int > b_int + 20)
        total_red = int(red_mask.sum())
        
        # Save debug info if requested
        debug_mask = (red_mask.astype(np.uint8) * 255) if return_debug else None
        debug_bbox = (x1, y1, x2, y2) if return_debug else None
        
        bbox_area = roi_w * roi_h
        
        # Simple threshold: need at least some red pixels
        # Adaptive based on size
        if bbox_area < 900:      # Tiny
            threshold = 2
        elif bbox_area < 2500:   # Small
            threshold = 5
        else:                    # Normal
            threshold = 10
        
        has_red = total_red >= threshold
        return (has_red, debug_mask, debug_bbox)

    def _has_red_edge(self, frame: np.ndarray, bbox: np.ndarray,
                       ratio_thresh: float = 0.02) -> bool:
        """Legacy wrapper for _check_red_edge, returns only boolean."""
        result, _, _ = self._check_red_edge(frame, bbox, ratio_thresh, return_debug=False)
        return result

    def detect(self, frame: np.ndarray) -> List[Detection]:
        results = self.model.predict(
            frame,
            conf=self.config.conf_threshold,
            iou=self.config.iou_threshold,
            device=self.config.device,
            imgsz=self.config.imgsz,
            half=getattr(self, '_use_half', False),
            verbose=False,
            max_det=10,   # Limit max detections to reduce GPU load
        )

        detections = []
        
        # Process results (returns list even for single image)
        if results and len(results) > 0:
            result = results[0]
            if result.boxes is not None and result.keypoints is not None:
                boxes = result.boxes.xyxy.cpu().numpy()
                confs = result.boxes.conf.cpu().numpy()
                keypoints = result.keypoints.data.cpu().numpy()

                for i in range(len(boxes)):
                    detection = Detection(
                        bbox=boxes[i],
                        confidence=float(confs[i]),
                        keypoints=keypoints[i]
                    )
                    detections.append(detection)

        # Mark each detection with red-edge flag (don't filter — let
        # downstream decide targeting; all persons stay visible on screen).
        if self.config.red_edge_filter and detections:
            debug_mode = getattr(self.config, 'debug_red_edge', False)
            # Limit red edge detection to max 5 detections to reduce overhead
            for i, d in enumerate(detections[:5]):
                has_red, debug_mask, debug_bbox = self._check_red_edge(
                    frame, d.bbox, return_debug=debug_mode
                )
                d.has_red_edge = has_red
                if debug_mode and debug_mask is not None and debug_bbox is not None:
                    # Store just the ROI mask and bbox, not full frame
                    d.debug_red_mask = debug_mask
                    d._debug_bbox = debug_bbox

        return detections

    def detect_batch(self, frames: List[np.ndarray]) -> List[List[Detection]]:
        return [self.detect(frame) for frame in frames]


def _is_file(path: str) -> bool:
    import os
    try:
        return os.path.isfile(path)
    except Exception:
        return False
