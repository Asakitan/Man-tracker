"""
Global hotkey listener
"""
import threading
from typing import Callable, Dict, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from config import HotkeyConfig, HotkeyBinding
from utils.obfuscation import _s


MOUSE_BUTTON_NAMES = {
    "mouse_left": _s("ml"),
    "mouse_right": _s("mr"),
    "mouse_middle": _s("mm"),
    "mouse_x1": _s("mx1"),
    "mouse_x2": _s("mx2"),
}


def _normalize_key(key) -> str:
    from pynput import keyboard

    if isinstance(key, keyboard.Key):
        _map = {
            keyboard.Key.f1: "f1", keyboard.Key.f2: "f2",
            keyboard.Key.f3: "f3", keyboard.Key.f4: "f4",
            keyboard.Key.f5: "f5", keyboard.Key.f6: "f6",
            keyboard.Key.f7: "f7", keyboard.Key.f8: "f8",
            keyboard.Key.f9: "f9", keyboard.Key.f10: "f10",
            keyboard.Key.f11: "f11", keyboard.Key.f12: "f12",
            keyboard.Key.space: "space",
            keyboard.Key.enter: "enter",
            keyboard.Key.tab: "tab",
            keyboard.Key.esc: "esc",
            keyboard.Key.backspace: "backspace",
            keyboard.Key.delete: "delete",
            keyboard.Key.insert: "insert",
            keyboard.Key.home: "home",
            keyboard.Key.end: "end",
            keyboard.Key.page_up: "page_up",
            keyboard.Key.page_down: "page_down",
            keyboard.Key.up: "up",
            keyboard.Key.down: "down",
            keyboard.Key.left: "left",
            keyboard.Key.right: "right",
            keyboard.Key.caps_lock: "caps_lock",
            keyboard.Key.num_lock: "num_lock",
        }
        return _map.get(key, key.name if hasattr(key, 'name') else str(key))
    elif isinstance(key, keyboard.KeyCode):
        if key.char:
            return key.char.lower()
        elif key.vk is not None:
            return f"vk_{key.vk}"
    return ""


def _normalize_mouse_button(button) -> str:
    from pynput import mouse
    _map = {
        mouse.Button.left: "mouse_left",
        mouse.Button.right: "mouse_right",
        mouse.Button.middle: "mouse_middle",
    }
    # x1/x2 may not exist in all pynput versions
    for attr, name in (("x1", "mouse_x1"), ("x2", "mouse_x2"),
                        ("button8", "mouse_x1"), ("button9", "mouse_x2")):
        btn = getattr(mouse.Button, attr, None)
        if btn is not None and btn not in _map:
            _map[btn] = name

    result = _map.get(button)
    if result:
        return result

    # Fallback: inspect raw value for X-buttons (Windows XBUTTON1=4, XBUTTON2=5)
    try:
        val = button.value if hasattr(button, 'value') else None
        if val == 4 or (hasattr(button, 'name') and 'x1' in str(button.name).lower()):
            return "mouse_x1"
        if val == 5 or (hasattr(button, 'name') and 'x2' in str(button.name).lower()):
            return "mouse_x2"
    except Exception:
        pass
    return ""


_ACTION_FIELDS = [
    "toggle_tracking",
    "quit",
    "toggle_auto_click",
    "toggle_visibility",
    "increase_smoothing",
    "decrease_smoothing",
    "increase_speed",
    "decrease_speed",
]


class HotkeyListener(QObject):

    action_triggered = pyqtSignal(str, bool)

    def __init__(self, config: HotkeyConfig, initial_toggle_states: Optional[Dict[str, bool]] = None, parent=None):
        super().__init__(parent)
        self._config = config
        self._kb_listener = None
        self._mouse_listener = None
        self._lock = threading.Lock()

        # toggle state tracking - can be pre-initialized to sync with UI
        self._toggle_states: Dict[str, bool] = initial_toggle_states.copy() if initial_toggle_states else {}
        # prevent long-press repeats
        self._pressed_keys: set = set()

    def start(self):
        from pynput import keyboard, mouse

        # always_on
        for field in _ACTION_FIELDS:
            binding: HotkeyBinding = getattr(self._config, field)
            if binding.mode == "always_on":
                self._toggle_states[field] = True
                self.action_triggered.emit(field, True)

        self._kb_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._kb_listener.daemon = True
        self._kb_listener.start()

        self._mouse_listener = mouse.Listener(
            on_click=self._on_mouse_click,
        )
        self._mouse_listener.daemon = True
        self._mouse_listener.start()



    def stop(self):
        if self._kb_listener:
            self._kb_listener.stop()
            self._kb_listener = None
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
        self._pressed_keys.clear()
        self._toggle_states.clear()


    def update_config(self, config: HotkeyConfig):
        with self._lock:
            self._config = config

    def _on_key_press(self, key):
        try:
            key_name = _normalize_key(key)
            if not key_name:
                return
            self._handle_press(key_name)
        except Exception as e:
            pass

    def _on_key_release(self, key):
        try:
            key_name = _normalize_key(key)
            if not key_name:
                return
            self._handle_release(key_name)
        except Exception as e:
            pass

    def _on_mouse_click(self, x, y, button, pressed):
        try:
            key_name = _normalize_mouse_button(button)
            if not key_name:
                return
            if pressed:
                self._handle_press(key_name)
            else:
                self._handle_release(key_name)
        except Exception as e:
            pass

    _MOUSE_KEYS = frozenset({"mouse_left", "mouse_right", "mouse_middle", "mouse_x1", "mouse_x2"})

    def _handle_press(self, key_name: str):
        with self._lock:
            if key_name in self._pressed_keys:
                return
            self._pressed_keys.add(key_name)

            key_lower = key_name.lower()
            pressed_lower = {k.lower() for k in self._pressed_keys}

            # --- mouse_left priority: suppress other mouse single-key actions
            if key_lower == "mouse_left":
                for field in _ACTION_FIELDS:
                    binding: HotkeyBinding = getattr(self._config, field)
                    if binding.mode != "hold":
                        continue
                    primary = binding.key.lower()
                    secondary = getattr(binding, 'secondary_key', '').lower()
                    # Deactivate hold actions bound to non-left mouse keys
                    keys_set = {primary} | ({secondary} if secondary else set())
                    if keys_set <= self._MOUSE_KEYS and "mouse_left" not in keys_set:
                        if keys_set & pressed_lower:
                            self.action_triggered.emit(field, False)

            for field in _ACTION_FIELDS:
                binding: HotkeyBinding = getattr(self._config, field)
                if binding.mode == "always_on":
                    continue

                primary = binding.key.lower()
                secondary = getattr(binding, 'secondary_key', '').lower()

                # OR logic: either primary or secondary triggers the action
                bound_keys = {primary}
                if secondary:
                    bound_keys.add(secondary)

                if key_lower not in bound_keys:
                    continue

                # Suppress non-left mouse single-key trigger while left is held
                if (bound_keys <= self._MOUSE_KEYS
                        and "mouse_left" not in bound_keys
                        and "mouse_left" in pressed_lower):
                    continue

                if binding.mode == "toggle":
                    current = self._toggle_states.get(field, False)
                    self._toggle_states[field] = not current
                    self.action_triggered.emit(field, not current)
                elif binding.mode == "hold":
                    self.action_triggered.emit(field, True)

    def _handle_release(self, key_name: str):
        with self._lock:
            self._pressed_keys.discard(key_name)
            key_lower = key_name.lower()

            for field in _ACTION_FIELDS:
                binding: HotkeyBinding = getattr(self._config, field)
                if binding.mode != "hold":
                    continue

                primary = binding.key.lower()
                secondary = getattr(binding, 'secondary_key', '').lower()
                bound_keys = {primary}
                if secondary:
                    bound_keys.add(secondary)

                # OR logic: release when ANY bound key is released
                #   but only if no other bound key is still held
                if key_lower in bound_keys:
                    still_held = bound_keys & {k.lower() for k in self._pressed_keys}
                    if not still_held:
                        self.action_triggered.emit(field, False)
