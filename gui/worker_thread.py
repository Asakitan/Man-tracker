"""
Video processing worker thread
"""
import cv2
import time
import traceback
import numpy as np
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker

from config import AppConfig, SkeletonPoint
# Lazy imports to avoid blocking GUI startup
# from core import PoseDetector, ByteTracker, MouseController
# from utils import Visualizer, VideoSource, VideoWriter, FPSCounter


class ProcessingThread(QThread):

    # ---- signals ----
    frame_ready = pyqtSignal(np.ndarray)
    stats_updated = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    finished_clean = pyqtSignal()
    model_loaded = pyqtSignal()

    def __init__(self, config: AppConfig, source_type: str = "file",
                 source_kwargs: dict = None, parent=None):
        super().__init__(parent)
        self.config = config
        self._source_type = source_type
        self._source_kwargs = source_kwargs or {}
        self._mutex = QMutex()
        self._running = False
        self._paused = False
        self._just_resumed = False

        # Runtime-modifiable params
        self._smoothing = config.mouse.smoothing_factor
        self._speed = config.mouse.mouse_speed
        self._skeleton_point = config.mouse.target_skeleton_point
        self._mouse_enabled = config.mouse.enable_mouse_control
        self._target_id: Optional[int] = config.mouse.target_track_id
        self._auto_click_enabled = config.mouse.auto_click_enabled
        self._arrival_threshold = config.mouse.arrival_threshold

    # ---------- public API ----------

    def set_smoothing(self, value: float):
        with QMutexLocker(self._mutex):
            self._smoothing = value

    def set_speed(self, value: float):
        with QMutexLocker(self._mutex):
            self._speed = value

    def set_skeleton_point(self, point: SkeletonPoint):
        with QMutexLocker(self._mutex):
            self._skeleton_point = point

    def set_mouse_enabled(self, enabled: bool):
        with QMutexLocker(self._mutex):
            self._mouse_enabled = enabled

    def set_target_id(self, tid: Optional[int]):
        with QMutexLocker(self._mutex):
            self._target_id = tid

    def set_auto_click_enabled(self, enabled: bool):
        with QMutexLocker(self._mutex):
            self._auto_click_enabled = enabled

    def toggle_pause(self):
        with QMutexLocker(self._mutex):
            self._paused = not self._paused

    def set_paused(self, paused: bool):
        with QMutexLocker(self._mutex):
            was_paused = self._paused
            self._paused = paused
            # Signal resume so mouse controller can reset auto-click state
            if was_paused and not paused:
                self._just_resumed = True

    @property
    def is_paused(self) -> bool:
        with QMutexLocker(self._mutex):
            return self._paused

    def stop(self):
        with QMutexLocker(self._mutex):
            self._running = False

    # ---------- main loop ----------

    def _is_dll_error(self, e: Exception) -> bool:
        msg = str(e).lower()
        return any(k in msg for k in ("dll", "1114", "c10.dll", "torch_cpu", "动态链接库"))

    def _dll_error_msg(self, e: Exception) -> str:
        # Find torch/lib location for diagnostics
        torch_lib_path = "?"
        try:
            import importlib.util
            spec = importlib.util.find_spec("torch")
            if spec and spec.origin:
                torch_lib_path = os.path.join(os.path.dirname(spec.origin), "lib")
        except Exception:
            pass

        return (
            "PyTorch DLL dependency error\n\n"
            "1. Install Visual C++ Redistributable:\n"
            "   https://aka.ms/vs/17/release/vc_redist.x64.exe\n\n"
            "2. Or reinstall PyTorch (CUDA):\n"
            "   pip install torch torchvision --index-url "
            "https://download.pytorch.org/whl/cu128\n\n"
            "3. Check NVIDIA driver ≥ CUDA 12.x:\n"
            "   nvidia-smi\n\n"
            f"torch/lib: {torch_lib_path}\n"
            f"Detail: {e}"
        )

    def run(self):  # noqa: C901
        try:
            import os

            try:
                from core import PoseDetector, ByteTracker, MouseController
                from utils import Visualizer, VideoSource, VideoWriter, FPSCounter
            except (OSError, RuntimeError, ImportError) as e:
                if self._is_dll_error(e):
                    self.error_occurred.emit(self._dll_error_msg(e))
                    return
                raise

            # --- init ---
            detector = PoseDetector(self.config.detector)
            tracker = ByteTracker(self.config.tracker)
            mouse_ctrl = MouseController(self.config.mouse, self.config.kmbox,
                                         aim_curve_config=self.config.aim_curve)
            visualizer = Visualizer(self.config.visualization)
            fps_counter = FPSCounter()

            # --- KMBOX-NET auto-connect ---
            print(f"[Worker] kmbox config: enabled={self.config.kmbox.enabled} ip={self.config.kmbox.ip}:{self.config.kmbox.port} mac={self.config.kmbox.mac}")
            # Auto-enable KMBOX when valid (non-default) settings exist
            _km = self.config.kmbox
            _has_valid_cfg = (_km.ip != "192.168.2.188" or _km.port != 8312 or _km.mac != "12345678")
            if _km.enabled or _has_valid_cfg:
                if not _km.enabled:
                    print("[Worker] KMBOX has valid config but was disabled, auto-enabling...")
                    _km.enabled = True
                ok = mouse_ctrl.connect_kmbox()
                print(f"[Worker] KMBOX connect result: {ok}")
                if ok and mouse_ctrl._kmbox:
                    mouse_ctrl._kmbox.test_move()  # Visual verify: cursor should twitch
            else:
                print("[Worker] KMBOX disabled and no valid config, skipping connect")

            self.model_loaded.emit()

            # --- create video source ---
            from utils.screen_capture import create_video_source, ScreenCaptureSource, WindowCaptureSource
            video = create_video_source(self._source_type, **self._source_kwargs)
            frame_size = video.size

            # --- set MouseController coordinate mapping ---
            if isinstance(video, ScreenCaptureSource):
                origin = (video._monitor["left"], video._monitor["top"])
                mouse_ctrl.set_source_info("offset", origin)
            elif isinstance(video, WindowCaptureSource):
                # window client area origin
                try:
                    import win32gui
                    pt = win32gui.ClientToScreen(video._hwnd, (0, 0))
                    mouse_ctrl.set_source_info("offset", pt)
                except Exception:
                    mouse_ctrl.set_source_info("offset", (0, 0))
            else:
                mouse_ctrl.set_source_info("proportional")

            writer: Optional[VideoWriter] = None
            if self.config.video.save_video and self.config.video.output_path:
                writer = VideoWriter(
                    self.config.video.output_path, video.size, video.fps
                )

            self._running = True
            detect_interval = max(1, self.config.detector.detect_interval)
            frame_idx = 0
            last_detections = []

            for frame in video.frames():
                # --- check stop ---
                with QMutexLocker(self._mutex):
                    if not self._running:
                        break

                # --- pause ---
                while True:
                    with QMutexLocker(self._mutex):
                        if not self._paused or not self._running:
                            break
                    self.msleep(50)

                with QMutexLocker(self._mutex):
                    if not self._running:
                        break

                # --- scale ---
                scale = self.config.video.process_scale
                if 0 < scale < 1.0:
                    small = cv2.resize(
                        frame, None, fx=scale, fy=scale,
                        interpolation=cv2.INTER_LINEAR,
                    )
                else:
                    small = frame

                # --- sync params ---
                with QMutexLocker(self._mutex):
                    mouse_ctrl.config.smoothing_factor = self._smoothing
                    mouse_ctrl.config.mouse_speed = self._speed
                    mouse_ctrl.config.target_skeleton_point = self._skeleton_point
                    mouse_ctrl.config.enable_mouse_control = self._mouse_enabled
                    mouse_ctrl.config.target_track_id = self._target_id
                    mouse_ctrl.config.auto_click_enabled = self._auto_click_enabled
                    mouse_ctrl.config.arrival_threshold = self._arrival_threshold
                    mouse_ctrl._red_edge_filter_on = self.config.detector.red_edge_filter
                    # Reset auto-click state when resuming from pause
                    if self._just_resumed:
                        self._just_resumed = False
                        mouse_ctrl._clicking = False
                        mouse_ctrl._arrival_clicked = False
                        mouse_ctrl._last_click_time = 0.0

                # --- dynamic KMBOX connect (in case user clicks connect after start) ---
                if self.config.kmbox.enabled and not mouse_ctrl.kmbox_connected:
                    print("[Worker] KMBOX enabled but not connected, trying to connect...")
                    # Recreate device with latest config (user may have changed IP/port/mac)
                    mouse_ctrl.set_backend("kmbox", self.config.kmbox)
                    print(f"[Worker] Dynamic KMBOX connect: {mouse_ctrl.kmbox_connected}")

                # --- detect + track ---
                if frame_idx % detect_interval == 0:
                    detections = detector.detect(small)

                    # remap coords to original size if scaled
                    if 0 < scale < 1.0:
                        inv = 1.0 / scale
                        for det in detections:
                            det.bbox = det.bbox * inv
                            det.keypoints[:, :2] *= inv

                    last_detections = detections
                else:
                    detections = last_detections

                frame_idx += 1

                tracks = tracker.update(detections)

                # --- mouse control ---
                mouse_pos = mouse_ctrl.update(tracks, frame_size)

                # --- visualization ---
                out = frame.copy()
                target_track = mouse_ctrl.select_target_track(tracks, frame_size)
                target_id = target_track.track_id if target_track else None

                if tracks:
                    out = visualizer.draw_tracks(
                        out, tracks,
                        self._target_id,
                        self._skeleton_point.value,
                        active_target_track=target_track,
                    )

                fps = fps_counter.update()

                # emit frame
                self.frame_ready.emit(out)

                # emit stats
                self.stats_updated.emit({
                    "fps": fps,
                    "track_count": len(tracks),
                    "target_id": target_id,
                    "target_point": self._skeleton_point.name,
                    "mouse_pos": mouse_pos,
                    "mouse_enabled": self._mouse_enabled,
                    "smoothing": self._smoothing,
                    "speed": self._speed,
                    "paused": self._paused,
                    "mouse_backend": mouse_ctrl.backend_name,
                })

                if writer:
                    writer.write(out)

            # --- cleanup ---
            if writer:
                writer.release()
            video.release()
            mouse_ctrl.cleanup()
            self.finished_clean.emit()

        except Exception as e:
            if self._is_dll_error(e):
                self.error_occurred.emit(self._dll_error_msg(e))
            else:
                self.error_occurred.emit(f"{e}\n{traceback.format_exc()}")
