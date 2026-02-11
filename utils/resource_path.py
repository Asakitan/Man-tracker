"""
Resource path utilities for packaged (PyInstaller) and development environments
"""
import sys
import os
from pathlib import Path


def resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource file.
    Works both in development mode and when packaged with PyInstaller.
    """
    if getattr(sys, 'frozen', False):
        # Running as a packaged executable (PyInstaller)
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        # Running in development
        base_path = str(Path(__file__).resolve().parent.parent)
    return os.path.join(base_path, relative_path)


def is_frozen() -> bool:
    """Check if running in a packaged (frozen) environment"""
    return getattr(sys, 'frozen', False)


def app_dir() -> str:
    """
    Get the application directory.
    In frozen mode: directory containing the exe.
    In dev mode: project root.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return str(Path(__file__).resolve().parent.parent)


def config_dir() -> str:
    """
    Get the writable config directory.
    In frozen mode: same as app_dir (next to the exe).
    In dev mode: project root.
    """
    return app_dir()
