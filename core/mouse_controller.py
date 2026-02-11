"""
Mouse controller — KMBOX-NET only.
"""
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass
import ctypes
import time
import threading
import random

from config import MouseConfig, KmboxConfig, SkeletonPoint, AimCurveConfig as _AppAimCurveConfig
from .tracker import Track
from .kmbox_net import KmboxNetDevice, KmboxConfig as _KmboxDevConfig
from .aim_curve import AimCurveEngine, AimCurveConfig


@dataclass
class MouseState:
    """Mouse state."""
    target_x: float = 0.0
    target_y: float = 0.0
    last_update_time: float = 0
    is_tracking: bool = False


class MouseController:
    """Mouse controller — KMBOX-NET backend."""

    def __init__(self, config: MouseConfig, kmbox_config: Optional[KmboxConfig] = None,
                 aim_curve_config: Optional[_AppAimCurveConfig] = None):
        self.config = config
        self.state = MouseState()
        self._screen_size = self._get_screen_size()
        print(f"[MouseCtrl] init  screen={self._screen_size}")

        # ── KMBOX-NET device ──
        self._kmbox: Optional[KmboxNetDevice] = None
        self._kmbox_config = kmbox_config

        if kmbox_config:
            print(f"[MouseCtrl] kmbox_config: enabled={kmbox_config.enabled} ip={kmbox_config.ip}:{kmbox_config.port}")
            self._init_kmbox(kmbox_config)
        else:
            print("[MouseCtrl] no kmbox_config provided")

        # Capture source info — set by worker after creating video source
        self._mapping_mode: str = "proportional"
        self._source_origin: Tuple[int, int] = (0, 0)

        # ── Humanized aim curve engine ──
        ac_cfg = AimCurveConfig()
        if aim_curve_config:
            # Copy matching fields from app config to engine config
            for fname in AimCurveConfig.__dataclass_fields__:
                if hasattr(aim_curve_config, fname):
                    setattr(ac_cfg, fname, getattr(aim_curve_config, fname))
        self._aim_curve = AimCurveEngine(
            screen_center=(self._screen_size[0] / 2.0, self._screen_size[1] / 2.0),
            config=ac_cfg,
        )
        self._last_target_id: Optional[int] = None  # Track target switches

        # Previous frame dx/dy for damping (legacy, kept for compat)
        self._prev_dx = 0.0
        self._prev_dy = 0.0

        # Auto-click state
        self._arrival_clicked = False
        self._clicking = False
        self._last_click_time: float = 0.0

    # ── KMBOX-NET management ──

    def _init_kmbox(self, kmbox_config: KmboxConfig):
        try:
            dev_cfg = _KmboxDevConfig(
                enabled=True,
                ip=kmbox_config.ip,
                port=kmbox_config.port,
                mac=kmbox_config.mac,
                timeout=kmbox_config.timeout,
            )
            self._kmbox = KmboxNetDevice(dev_cfg)
            print(f"[MouseCtrl] KmboxNetDevice created: {kmbox_config.ip}:{kmbox_config.port} mac={kmbox_config.mac}")
        except Exception as e:
            print(f"[MouseCtrl] _init_kmbox FAILED: {e}")
            self._kmbox = None

    def connect_kmbox(self) -> bool:
        # If device not yet created but we have config, create it now
        if self._kmbox is None and self._kmbox_config is not None:
            print("[MouseCtrl] connect_kmbox: device is None, creating from stored config...")
            self._init_kmbox(self._kmbox_config)
        if self._kmbox is None:
            print("[MouseCtrl] connect_kmbox: FAILED - no device")
            return False
        ok = self._kmbox.connect()
        print(f"[MouseCtrl] connect_kmbox: result={ok} is_connected={self._kmbox.is_connected}")
        return ok

    def disconnect_kmbox(self):
        if self._kmbox:
            self._kmbox.close()

    @property
    def kmbox_connected(self) -> bool:
        return self._kmbox is not None and self._kmbox.is_connected

    @property
    def backend_name(self) -> str:
        return "KMBOX-NET"

    def set_source_info(self, mode: str, origin: Tuple[int, int] = (0, 0)):
        self._mapping_mode = mode
        self._source_origin = origin

    # ── Internal utilities ──

    @staticmethod
    def _get_screen_size() -> Tuple[int, int]:
        try:
            _u32 = ctypes.windll.user32
            return (_u32.GetSystemMetrics(0), _u32.GetSystemMetrics(1))
        except Exception:
            return (1920, 1080)

    def _map_to_screen(
        self,
        point: Tuple[float, float],
        frame_size: Tuple[int, int],
    ) -> Tuple[float, float]:
        x, y = point
        if self._mapping_mode == "offset":
            ox, oy = self._source_origin
            return (ox + x, oy + y)
        else:
            fw, fh = frame_size
            sw, sh = self._screen_size
            return (x / fw * sw, y / fh * sh)

    # ── Core movement ──

    def _calc_and_move(self, screen_x: float, screen_y: float):
        speed = getattr(self.config, "mouse_speed", 1.0)
        smooth = max(self.config.smoothing_factor, 0.01)

        # Compute humanized delta via curve engine
        dx, dy = self._aim_curve.update(screen_x, screen_y, speed, smooth)

        if dx == 0 and dy == 0:
            return

        # Debug logging (throttled)
        if not hasattr(self, '_move_log_counter'):
            self._move_log_counter = 0
        self._move_log_counter += 1
        if self._move_log_counter % 60 == 1:
            cx, cy = self._screen_size[0] / 2.0, self._screen_size[1] / 2.0
            dist = ((screen_x - cx) ** 2 + (screen_y - cy) ** 2) ** 0.5
            connected = self._kmbox.is_connected if self._kmbox else False
            mode = self._aim_curve.cfg.curve_mode
            print(f"[MouseCtrl] move dx={dx} dy={dy} dist={dist:.0f} mode={mode} kmbox={connected}")

        # Skip move during click to avoid button-state interference
        if self._clicking:
            return

        # Send via KMBOX-NET (interpolation handled async, no blocking)
        if self._kmbox and self._kmbox.is_connected:
            # Get interpolated micro-moves
            moves = self._aim_curve.get_interpolated_moves(dx, dy)
            for move_dx, move_dy, delay in moves:
                if move_dx == 0 and move_dy == 0:
                    continue
                ok = self._kmbox.move(move_dx, move_dy)
                if not ok and self._move_log_counter % 60 == 1:
                    print(f"[MouseCtrl] move SEND FAILED: dx={move_dx} dy={move_dy}")
                # Skip delay to avoid blocking main loop - KMBOX handles buffering
        elif not hasattr(self, '_move_warn_logged'):
            self._move_warn_logged = True
            print(f"[MouseCtrl] move SKIPPED: kmbox={self._kmbox is not None} connected={self._kmbox.is_connected if self._kmbox else 'N/A'}")

    # ── Keypoint extraction ──

    def get_target_keypoint(self, track: Track) -> Optional[Tuple[float, float]]:
        keypoint_idx = self.config.target_skeleton_point.value
        kp = track.detection.get_keypoint(keypoint_idx)
        if kp is not None:
            return (kp[0], kp[1])
        return None

    def select_target_track(self, tracks: list, frame_size: Tuple[int, int] = None) -> Optional[Track]:
        if not tracks:
            return None

        # When red-edge filter is active, only consider enemy tracks
        # EXCEPTION: If we're already tracking a target, keep tracking it even if red edge is lost
        red_filter_on = getattr(self, '_red_edge_filter_on', True)
        current_target_id = self._last_target_id  # Currently tracked target
        
        candidates = tracks
        if red_filter_on:
            # Build candidate list: enemies + current target (if still visible)
            enemy_tracks = [t for t in tracks if getattr(t.detection, 'has_red_edge', False)]
            
            # If we're tracking a target, include it even without red edge
            current_target = None
            if current_target_id is not None:
                for t in tracks:
                    if t.track_id == current_target_id:
                        current_target = t
                        break
            
            # Merge: current target (priority) + enemies
            if current_target and current_target not in enemy_tracks:
                candidates = [current_target] + enemy_tracks
            else:
                candidates = enemy_tracks
            
            if not candidates:
                return None

        # target_track_id=None or 0 means "auto-select nearest to screen center"
        if self.config.target_track_id is not None and self.config.target_track_id != 0:
            for track in candidates:
                if track.track_id == self.config.target_track_id:
                    return track
            return None

        cx = self._screen_size[0] / 2.0
        cy = self._screen_size[1] / 2.0
        best = None
        best_dist = float('inf')
        for track in candidates:
            bx, by = track.detection.center
            if frame_size:
                sx, sy = self._map_to_screen((bx, by), frame_size)
            else:
                sx, sy = bx, by
            dist = (sx - cx) ** 2 + (sy - cy) ** 2
            if dist < best_dist:
                best_dist = dist
                best = track
        return best

    # ── Main update ──

    def update(
        self,
        tracks: list,
        frame_size: Tuple[int, int],
    ) -> Optional[Tuple[int, int]]:
        if not self.config.enable_mouse_control:
            return None

        target_track = self.select_target_track(tracks, frame_size)
        if target_track is None:
            self.state.is_tracking = False
            # Only reset target ID if no tracks at all (target truly lost)
            # This allows continuing to track a target that temporarily loses red edge
            if not tracks:
                self._last_target_id = None
            return None

        # Reset curve engine when switching targets
        current_tid = target_track.track_id
        if current_tid != self._last_target_id:
            self._aim_curve.reset()
            self._last_target_id = current_tid
            # Reset auto-click state for new target
            self._arrival_clicked = False
            self._last_click_time = 0.0

        keypoint = self.get_target_keypoint(target_track)
        if keypoint is None:
            self.state.is_tracking = False
            return None

        sx, sy = self._map_to_screen(keypoint, frame_size)

        self.state.target_x = sx
        self.state.target_y = sy
        self.state.is_tracking = True
        self.state.last_update_time = time.time()

        self._calc_and_move(sx, sy)

        # ── Auto-click on arrival (any visible keypoint) ──
        if getattr(self.config, 'auto_click_enabled', False):
            cx = self._screen_size[0] / 2.0
            cy = self._screen_size[1] / 2.0
            threshold = getattr(self.config, 'arrival_threshold', 5.0)

            # Check distance from screen center to ALL visible keypoints
            min_dist = float('inf')
            for kp_idx in range(17):  # COCO 17 keypoints
                kp = target_track.detection.get_keypoint(kp_idx)
                if kp is None:
                    continue
                kx, ky = self._map_to_screen((kp[0], kp[1]), frame_size)
                d = ((kx - cx) ** 2 + (ky - cy) ** 2) ** 0.5
                if d < min_dist:
                    min_dist = d

            if min_dist < threshold:
                # Fixed interval repeat: 100ms ± 20ms (configurable)
                base_interval = getattr(self.config, 'auto_click_interval', 0.1)
                jitter = getattr(self.config, 'auto_click_jitter', 0.02)
                interval = base_interval + random.uniform(-jitter, jitter)
                now = time.time()
                if not self._clicking and (now - self._last_click_time) >= interval:
                    self._do_auto_click()
            else:
                self._arrival_clicked = False

        return (int(sx), int(sy))

    # ── Settings methods ──

    def set_target_skeleton_point(self, point: SkeletonPoint):
        self.config.target_skeleton_point = point

    def set_target_track_id(self, track_id: Optional[int]):
        self.config.target_track_id = track_id

    def enable(self):
        self.config.enable_mouse_control = True

    def disable(self):
        self.config.enable_mouse_control = False

    def reset(self):
        self.state = MouseState()
        self._arrival_clicked = False
        self._clicking = False
        self._aim_curve.reset()
        self._last_target_id = None

    def set_backend(self, backend: str, kmbox_config: Optional[KmboxConfig] = None):
        """Reconfigure KMBOX-NET device."""
        if kmbox_config:
            self._kmbox_config = kmbox_config
            self._init_kmbox(kmbox_config)
        if self._kmbox:
            self.connect_kmbox()

    def cleanup(self):
        if self._kmbox:
            self._kmbox.close()
            self._kmbox = None
        self._arrival_clicked = False
        self._clicking = False

    # ── Auto-click helpers ──

    def _do_auto_click(self):
        """Trigger auto-click in a background thread to avoid blocking."""
        if self._clicking:
            return
        self._clicking = True
        t = threading.Thread(target=self._auto_click_worker, daemon=True)
        t.start()

    def _auto_click_worker(self):
        """
        Perform left click.
        Click hold: 50ms + 10~50ms random.
        """
        try:
            # Click hold duration
            duration = 50 + random.randint(10, 50)
            if self._kmbox:
                ok = self._kmbox.left_click(duration)
                self._last_click_time = time.time()
                if not ok:
                    print(f"[MouseCtrl] auto-click FAILED (send error)")
            else:
                print(f"[MouseCtrl] auto-click SKIPPED: no kmbox device")
        except Exception as e:
            print(f"[MouseCtrl] auto-click ERROR: {e}")
        finally:
            self._clicking = False
