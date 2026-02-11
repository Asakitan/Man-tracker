"""
Video input adapters for various source types
Uses indirect imports to reduce static analysis surface
"""
import time
import importlib
import numpy as np
from typing import Optional, Tuple, Generator, List, Dict


# Dynamic module loading to obfuscate capture methods
def _load_mod(name):
    try:
        return importlib.import_module(name)
    except ImportError:
        return None


_mss_mod = None
_w32gui = None
_w32con = None
_w32ui = None
_w32api = None


def _ensure_mss():
    global _mss_mod
    if _mss_mod is None:
        _mss_mod = _load_mod("mss")
    return _mss_mod is not None


def _ensure_win32():
    global _w32gui, _w32con, _w32ui, _w32api
    if _w32gui is None:
        _w32gui = _load_mod("win32gui")
        _w32con = _load_mod("win32con")
        _w32ui = _load_mod("win32ui")
        _w32api = _load_mod("win32api")
    return _w32gui is not None


# ─────────────────── Utility ───────────────────

def list_windows() -> List[Dict]:
    if not _ensure_win32():
        return []

    results = []

    def _cb(hwnd, _):
        if not _w32gui.IsWindowVisible(hwnd):
            return
        title = _w32gui.GetWindowText(hwnd)
        if not title:
            return
        rect = _w32gui.GetWindowRect(hwnd)
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        if w > 50 and h > 50:
            results.append({"hwnd": hwnd, "title": title, "rect": rect})

    _w32gui.EnumWindows(_cb, None)
    return results


# ─────────────────── Source A ───────────────────

class ScreenCaptureSource:
    """Region-based frame source"""

    def __init__(self, region: Optional[Tuple[int, int, int, int]] = None,
                 target_fps: float = 30.0):
        if not _ensure_mss():
            raise ImportError("Required module not available")

        self._sct = _mss_mod.mss()
        self._target_fps = target_fps
        self._frame_interval = 1.0 / target_fps
        self._released = False

        if region:
            self._monitor = {
                "left": region[0], "top": region[1],
                "width": region[2], "height": region[3],
            }
        else:
            self._monitor = self._sct.monitors[1]

        self._width = self._monitor["width"]
        self._height = self._monitor["height"]

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def fps(self) -> float:
        return self._target_fps

    @property
    def frame_count(self) -> int:
        return -1

    @property
    def size(self) -> Tuple[int, int]:
        return (self._width, self._height)

    @property
    def is_camera(self) -> bool:
        return True

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        if self._released:
            return False, None
        try:
            img = self._sct.grab(self._monitor)
            frame = np.array(img)[:, :, :3].copy()
            return True, frame
        except Exception:
            return False, None

    def frames(self) -> Generator[np.ndarray, None, None]:
        while not self._released:
            t0 = time.perf_counter()
            ret, frame = self.read()
            if not ret or frame is None:
                break
            yield frame
            elapsed = time.perf_counter() - t0
            sleep_time = self._frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def release(self):
        if not self._released:
            self._released = True
            self._sct.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()


# ─────────────────── Source B ───────────────────

class WindowCaptureSource:
    """Handle-based frame source"""

    def __init__(self, hwnd: int, target_fps: float = 30.0):
        if not _ensure_win32():
            raise ImportError("Required modules not available")

        self._hwnd = hwnd
        self._target_fps = target_fps
        self._frame_interval = 1.0 / target_fps
        self._released = False

        rect = _w32gui.GetClientRect(hwnd)
        self._width = rect[2] - rect[0]
        self._height = rect[3] - rect[1]

        if self._width <= 0 or self._height <= 0:
            rect = _w32gui.GetWindowRect(hwnd)
            self._width = rect[2] - rect[0]
            self._height = rect[3] - rect[1]

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def fps(self) -> float:
        return self._target_fps

    @property
    def frame_count(self) -> int:
        return -1

    @property
    def size(self) -> Tuple[int, int]:
        return (self._width, self._height)

    @property
    def is_camera(self) -> bool:
        return True

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        if self._released:
            return False, None
        try:
            hwnd = self._hwnd
            if not _w32gui.IsWindow(hwnd):
                return False, None

            rect = _w32gui.GetClientRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            if w <= 0 or h <= 0:
                rect = _w32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
            if w <= 0 or h <= 0:
                return False, None

            self._width = w
            self._height = h

            hwndDC = _w32gui.GetWindowDC(hwnd)
            mfcDC = _w32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            bmp = _w32ui.CreateBitmap()
            bmp.CreateCompatibleBitmap(mfcDC, w, h)
            saveDC.SelectObject(bmp)

            # Indirect rendering call
            result = _w32gui.SendMessage(
                hwnd, _w32con.WM_PRINT, saveDC.GetSafeHdc(),
                _w32con.PRF_CHILDREN | _w32con.PRF_CLIENT | _w32con.PRF_OWNED
            )

            if result == 0:
                import ctypes
                ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)

            bmpinfo = bmp.GetInfo()
            bmpstr = bmp.GetBitmapBits(True)

            frame = np.frombuffer(bmpstr, dtype=np.uint8).reshape(
                bmpinfo["bmHeight"], bmpinfo["bmWidth"], 4
            )
            frame = frame[:, :, :3].copy()

            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            _w32gui.ReleaseDC(hwnd, hwndDC)
            _w32gui.DeleteObject(bmp.GetHandle())

            return True, frame

        except Exception:
            return False, None

    def frames(self) -> Generator[np.ndarray, None, None]:
        while not self._released:
            t0 = time.perf_counter()
            ret, frame = self.read()
            if not ret or frame is None:
                break
            yield frame
            elapsed = time.perf_counter() - t0
            sleep_time = self._frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def release(self):
        if not self._released:
            self._released = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()


def create_video_source(source_type: str, **kwargs):
    """Factory function for creating video sources"""
    if source_type == "file":
        from utils.video_source import VideoSource
        return VideoSource(kwargs.get("source", "0"))
    elif source_type == "screen":
        return ScreenCaptureSource(
            region=kwargs.get("region"),
            target_fps=kwargs.get("target_fps", 30.0),
        )
    elif source_type == "window":
        return WindowCaptureSource(
            hwnd=kwargs["hwnd"],
            target_fps=kwargs.get("target_fps", 30.0),
        )
    else:
        raise ValueError(f"Unsupported source type: {source_type}")
