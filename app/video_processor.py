"""
Video processor
"""
import cv2
import numpy as np
from typing import Optional, Callable
import time

from config import AppConfig, SkeletonPoint
from core import PoseDetector, ByteTracker, MouseController, Track
from utils import Visualizer, VideoSource, VideoWriter, FPSCounter


class VideoProcessor:
    
    def __init__(self, config: AppConfig):
        self.config = config
        
        # init modules
        self.detector = PoseDetector(config.detector)
        self.tracker = ByteTracker(config.tracker)
        self.mouse_controller = MouseController(config.mouse)
        self.visualizer = Visualizer(config.visualization)
        self.fps_counter = FPSCounter()
        
        # state
        self.is_paused = False
        self.is_running = False
        self.current_frame_idx = 0
        
        # callback
        self._on_frame_callback: Optional[Callable] = None
    
    def set_on_frame_callback(self, callback: Callable[[np.ndarray, list], None]):
        self._on_frame_callback = callback
    
    def process_frame(self, frame: np.ndarray) -> tuple:
        # detect
        detections = self.detector.detect(frame)
        
        # track
        tracks = self.tracker.update(detections)
        
        # mouse control
        frame_size = (frame.shape[1], frame.shape[0])
        mouse_pos = self.mouse_controller.update(tracks, frame_size)
        
        # visualization
        output_frame = frame.copy()
        
        # active target ID
        target_track = self.mouse_controller.select_target_track(tracks)
        target_id = target_track.track_id if target_track else None
        
        # draw tracks
        if tracks:
            output_frame = self.visualizer.draw_tracks(
                output_frame,
                tracks,
                self.config.mouse.target_track_id,
                self.config.mouse.target_skeleton_point.value
            )
        
        # draw info panel
        fps = self.fps_counter.update()
        output_frame = self.visualizer.draw_info_panel(
            output_frame,
            fps=fps,
            track_count=len(tracks),
            target_id=target_id,
            target_point=self.config.mouse.target_skeleton_point.name,
            mouse_pos=mouse_pos
        )
        
        # draw help
        output_frame = self.visualizer.draw_help(output_frame)
        
        # callback
        if self._on_frame_callback:
            self._on_frame_callback(output_frame, tracks)
        
        return output_frame, tracks, mouse_pos
    
    def handle_key(self, key: int) -> bool:
        if key == ord('q') or key == ord('Q'):
            return False
        
        elif key == ord(' '):
            self.is_paused = not self.is_paused
        
        elif key == ord('m') or key == ord('M'):
            if self.config.mouse.enable_mouse_control:
                self.mouse_controller.disable()
            else:
                self.mouse_controller.enable()
        
        elif key == ord('s') or key == ord('S'):
            self._cycle_skeleton_point()
        
        elif ord('0') <= key <= ord('9'):
            if key == ord('0'):
                self.mouse_controller.set_target_track_id(None)
            else:
                track_id = key - ord('1')
                self.mouse_controller.set_target_track_id(track_id)
        
        return True
    
    def _cycle_skeleton_point(self):
        current = self.config.mouse.target_skeleton_point.value
        next_idx = (current + 1) % 17
        new_point = SkeletonPoint(next_idx)
        self.mouse_controller.set_target_skeleton_point(new_point)
        self.config.mouse.target_skeleton_point = new_point
    
    def run(self, source: str, output_path: Optional[str] = None):
        self.is_running = True
        writer = None
        
        try:
            video = VideoSource(source)
            
            # video writer
            if output_path:
                writer = VideoWriter(
                    output_path,
                    video.size,
                    video.fps
                )
            
            self.is_running = True
            
            if self.config.video.show_preview:
                cv2.namedWindow("Man Tracker", cv2.WINDOW_NORMAL)
            
            # main loop
            for frame in video.frames():
                if not self.is_running:
                    break
                
                # pause
                while self.is_paused:
                    key = cv2.waitKey(100) & 0xFF
                    if not self.handle_key(key):
                        self.is_running = False
                        break
                    if not self.is_paused:
                        break
                
                if not self.is_running:
                    break
                
                # process frame
                output_frame, tracks, mouse_pos = self.process_frame(frame)
                self.current_frame_idx += 1
                
                # write
                if writer:
                    writer.write(output_frame)
                
                # display
                if self.config.video.show_preview:
                    cv2.imshow("Man Tracker", output_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if not self.handle_key(key):
                        break
            
        except KeyboardInterrupt:
            pass
        
        except Exception as e:
            raise
        
        finally:
            self.is_running = False
            if writer:
                writer.release()
            if self.config.video.show_preview:
                cv2.destroyAllWindows()
            video.release()
    
    def stop(self):
        self.is_running = False
    
    def reset(self):
        self.tracker.reset()
        self.mouse_controller.reset()
        self.fps_counter.reset()
        self.current_frame_idx = 0
        self.is_paused = False
