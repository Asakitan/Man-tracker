"""
FPS calculation module
"""
import time
from collections import deque


class FPSCounter:
    """Frame rate counter"""
    
    def __init__(self, window_size: int = 30):
        """
        Initialize the frame rate counter.
        
        Args:
            window_size: Sliding window size
        """
        self.window_size = window_size
        self.timestamps = deque(maxlen=window_size)
        self._last_time = time.time()
    
    def update(self) -> float:
        """
        Update the counter and return the current frame rate.
        
        Returns:
            Current frame rate
        """
        current_time = time.time()
        self.timestamps.append(current_time)
        
        if len(self.timestamps) < 2:
            return 0.0
        
        # Calculate average FPS
        time_span = self.timestamps[-1] - self.timestamps[0]
        if time_span > 0:
            fps = (len(self.timestamps) - 1) / time_span
        else:
            fps = 0.0
        
        return fps
    
    def get_fps(self) -> float:
        """Get the current frame rate."""
        if len(self.timestamps) < 2:
            return 0.0
        
        time_span = self.timestamps[-1] - self.timestamps[0]
        if time_span > 0:
            return (len(self.timestamps) - 1) / time_span
        return 0.0
    
    def reset(self):
        """Reset the counter."""
        self.timestamps.clear()
        self._last_time = time.time()
