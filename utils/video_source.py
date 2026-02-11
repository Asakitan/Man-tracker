"""Video source module."""
import cv2
import numpy as np
from typing import Optional, Tuple, Generator
from pathlib import Path


class VideoSource:
    """Video source manager."""
    
    def __init__(self, source: str):
        """
        Initialize video source.
        
        Args:
            source: Video path or camera index (as string).
        """
        self.source = source
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_camera = False
        self._initialize()
    
    def _initialize(self):
        """Initialize video capture."""
        # Check if source is a camera
        if self.source.isdigit():
            self.is_camera = True
            self.cap = cv2.VideoCapture(int(self.source))
        else:
            # Video file
            if not Path(self.source).exists():
                raise FileNotFoundError(f"Video file not found: {self.source}")
            self.cap = cv2.VideoCapture(self.source)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open video source: {self.source}")
        
        print(f"[VideoSource] Opened: {self.source}")
        print(f"[VideoSource] Resolution: {self.width}x{self.height}")
        print(f"[VideoSource] FPS: {self.fps}")
        if not self.is_camera:
            print(f"[VideoSource] Total frames: {self.frame_count}")
    
    @property
    def width(self) -> int:
        """Video width."""
        return int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    
    @property
    def height(self) -> int:
        """Video height."""
        return int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    @property
    def fps(self) -> float:
        """Video FPS."""
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        return fps if fps > 0 else 30.0
    
    @property
    def frame_count(self) -> int:
        """Total frame count."""
        if self.is_camera:
            return -1
        return int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    @property
    def size(self) -> Tuple[int, int]:
        """Video dimensions (width, height)."""
        return (self.width, self.height)
    
    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read one frame.
        
        Returns:
            (success, frame)
        """
        if self.cap is None:
            return False, None
        return self.cap.read()
    
    def frames(self) -> Generator[np.ndarray, None, None]:
        """
        Frame generator.
        
        Yields:
            Video frame.
        """
        while True:
            ret, frame = self.read()
            if not ret:
                break
            yield frame
    
    def seek(self, frame_idx: int):
        """Seek to the specified frame."""
        if not self.is_camera and self.cap is not None:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    
    def get_position(self) -> int:
        """Get current frame position."""
        if self.cap is None:
            return 0
        return int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
    
    def release(self):
        """Release video source."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            print("[VideoSource] Released")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class VideoWriter:
    """Video writer."""
    
    def __init__(
        self, 
        output_path: str, 
        size: Tuple[int, int],
        fps: float = 30.0,
        codec: str = "mp4v"
    ):
        """
        Initialize video writer.
        
        Args:
            output_path: Output file path.
            size: Video dimensions (width, height).
            fps: Frame rate.
            codec: Video codec.
        """
        self.output_path = output_path
        self.size = size
        self.fps = fps
        
        fourcc = cv2.VideoWriter_fourcc(*codec)
        self.writer = cv2.VideoWriter(output_path, fourcc, fps, size)
        
        if not self.writer.isOpened():
            raise RuntimeError(f"Cannot create video writer: {output_path}")
        
        print(f"[VideoWriter] Output: {output_path}")
    
    def write(self, frame: np.ndarray):
        """Write one frame."""
        if self.writer is not None:
            self.writer.write(frame)
    
    def release(self):
        """Release writer."""
        if self.writer is not None:
            self.writer.release()
            self.writer = None
            print(f"[VideoWriter] Saved: {self.output_path}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
