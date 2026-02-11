"""
Core module - imports torch first to avoid circular import issues with ultralytics
"""
# CRITICAL: Import torch BEFORE any ultralytics-dependent modules
# ultralytics accesses torch.autograd during import, torch must be fully loaded first
import torch  # noqa: F401, E402

from .detector import PoseDetector, Detection
from .tracker import ByteTracker, Track, KalmanBoxTracker
from .mouse_controller import MouseController, MouseState
from .kmbox_net import KmboxNetDevice

__all__ = [
    "PoseDetector",
    "Detection",
    "ByteTracker",
    "Track",
    "KalmanBoxTracker",
    "MouseController",
    "MouseState",
    "KmboxNetDevice",
]
