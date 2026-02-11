"""
Hotkey editor panel
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QPushButton, QHBoxLayout, QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from PyQt6.QtGui import QKeySequence, QKeyEvent, QMouseEvent

from config import HotkeyConfig, HotkeyBinding
from gui.hotkey_listener import MOUSE_BUTTON_NAMES
from utils.obfuscation import _s

_HOTKEY_DEFS = [
    ("toggle_tracking", _s("hk_tracking")),
    ("quit", _s("hk_quit")),
    ("toggle_auto_click", "\u5230\u8fbe\u81ea\u52a8\u70b9\u51fb"),
    ("toggle_visibility", "\u663e\u793a/\u9690\u85cf\u7a97\u53e3"),
    ("increase_smoothing", _s("hk_inc_smooth")),
    ("decrease_smoothing", _s("hk_dec_smooth")),
    ("increase_speed", _s("hk_inc_speed")),
    ("decrease_speed", _s("hk_dec_speed")),
]

_MODE_LABELS = {
    "always_on": _s("mode_always"),
    "hold": _s("mode_hold"),
    "toggle": _s("mode_toggle"),
}
_MODE_FROM_LABEL = {v: k for k, v in _MODE_LABELS.items()}


class HotkeyEditor(QWidget):

    hotkeys_changed = pyqtSignal(object)

    def __init__(self, config: HotkeyConfig, parent=None):
        super().__init__(parent)
        self._config = config
        self._capturing_row: int = -1
        self._capturing_col: int = -1
        self._init_ui()
        self._load()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        tip = QLabel(
            "Click key column to rebind; Mode column for trigger type\n"
            "\u2022 Always on\n"
            "\u2022 Hold\n"
            "\u2022 Toggle\n"
            "Secondary key: Delete/Backspace to clear"
        )
        tip.setObjectName("subtitleLabel")
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #a6adc8; font-size: 12px; padding: 4px 0;")
        layout.addWidget(tip)

        self.table = QTableWidget(len(_HOTKEY_DEFS), 4)
        self.table.setHorizontalHeaderLabels([_s("hk_func"), _s("hk_key"), "\u526f\u952e", _s("hk_mode")])
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.resizeSection(1, 120)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hdr.resizeSection(2, 120)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hdr.resizeSection(3, 110)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.viewport().installEventFilter(self)
        layout.addWidget(self.table, stretch=1)

        # bottom buttons
        btn_row = QHBoxLayout()
        self.btn_reset = QPushButton(_s("hk_reset"))
        self.btn_reset.clicked.connect(self._reset)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_reset)
        layout.addLayout(btn_row)

        self._capture_label = QLabel("")
        self._capture_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._capture_label.setStyleSheet(
            "color: #f9e2af; font-size: 12px; padding: 4px;"
        )
        layout.addWidget(self._capture_label)

    def _load(self):
        for row, (field, label) in enumerate(_HOTKEY_DEFS):
            # Col 0: function name
            name_item = QTableWidgetItem(label)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, 0, name_item)

            # Col 1: key
            binding: HotkeyBinding = getattr(self._config, field)
            display_key = MOUSE_BUTTON_NAMES.get(binding.key, binding.key)
            key_item = QTableWidgetItem(display_key)
            key_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            key_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, key_item)

            # Col 2: secondary key
            secondary = getattr(binding, 'secondary_key', '')
            display_sec = MOUSE_BUTTON_NAMES.get(secondary, secondary) if secondary else ""
            sec_item = QTableWidgetItem(display_sec)
            sec_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            sec_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, sec_item)

            # Col 3: mode dropdown
            cmb = QComboBox()
            cmb.addItems(list(_MODE_LABELS.values()))
            cmb.setCurrentText(_MODE_LABELS.get(binding.mode, _s("mode_toggle")))
            cmb.currentTextChanged.connect(
                lambda text, r=row: self._on_mode_changed(r, text)
            )
            self.table.setCellWidget(row, 3, cmb)

    def _on_cell_clicked(self, row: int, col: int):
        if col in (1, 2):
            self._capturing_row = row
            self._capturing_col = col
            col_label = "\u4e3b\u952e" if col == 1 else "\u526f\u952e"
            self._capture_label.setText(
                f"\u6b63\u5728\u6355\u6349{col_label} - \u6309\u4e0b\u6309\u952e\u6216\u9f20\u6807\u952e... (Esc \u53d6\u6d88)"
            )
            self.table.item(row, col).setText("...")
            self.setFocus()

    def _on_mode_changed(self, row: int, text: str):
        field = _HOTKEY_DEFS[row][0]
        mode = _MODE_FROM_LABEL.get(text, "toggle")
        binding: HotkeyBinding = getattr(self._config, field)
        binding.mode = mode
        self.hotkeys_changed.emit(self._config)

    def keyPressEvent(self, event: QKeyEvent):  # noqa: N802
        if self._capturing_row < 0:
            super().keyPressEvent(event)
            return

        key = event.key()

        # Esc cancel
        if key == Qt.Key.Key_Escape:
            row = self._capturing_row
            col = self._capturing_col
            self._capturing_row = -1
            self._capturing_col = -1
            self._capture_label.setText("")
            field = _HOTKEY_DEFS[row][0]
            binding: HotkeyBinding = getattr(self._config, field)
            if col == 1:
                display = MOUSE_BUTTON_NAMES.get(binding.key, binding.key)
            else:
                sec = getattr(binding, 'secondary_key', '')
                display = MOUSE_BUTTON_NAMES.get(sec, sec) if sec else ""
            self.table.item(row, col).setText(display)
            return

        # Delete/Backspace clears secondary key
        if self._capturing_col == 2 and key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            row = self._capturing_row
            self._capturing_row = -1
            self._capturing_col = -1
            self._capture_label.setText("")
            self.table.item(row, 2).setText("")
            field = _HOTKEY_DEFS[row][0]
            binding: HotkeyBinding = getattr(self._config, field)
            binding.secondary_key = ""
            self.hotkeys_changed.emit(self._config)
            return

        # Ignore modifier-only keys
        if key in (
            Qt.Key.Key_Control, Qt.Key.Key_Shift,
            Qt.Key.Key_Alt, Qt.Key.Key_Meta,
        ):
            return

        key_name = _qt_key_to_name(key)
        if not key_name:
            return

        row = self._capturing_row
        col = self._capturing_col
        self._capturing_row = -1
        self._capturing_col = -1
        self._capture_label.setText("")

        # update table and config
        self.table.item(row, col).setText(key_name)
        field = _HOTKEY_DEFS[row][0]
        binding: HotkeyBinding = getattr(self._config, field)
        if col == 1:
            binding.key = key_name
        else:
            binding.secondary_key = key_name
        self.hotkeys_changed.emit(self._config)

    _MOUSE_MAP = {
        Qt.MouseButton.LeftButton: "mouse_left",
        Qt.MouseButton.RightButton: "mouse_right",
        Qt.MouseButton.MiddleButton: "mouse_middle",
        Qt.MouseButton.XButton1: "mouse_x1",
        Qt.MouseButton.XButton2: "mouse_x2",
    }

    def eventFilter(self, obj, event):  # noqa: N802
        """Intercept mouse clicks on the table viewport during capture."""
        if (
            self._capturing_row >= 0
            and obj is self.table.viewport()
            and event.type() == QEvent.Type.MouseButtonPress
        ):
            return self._handle_mouse_capture(event.button())
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event: QMouseEvent):  # noqa: N802
        if self._capturing_row < 0:
            super().mousePressEvent(event)
            return
        if not self._handle_mouse_capture(event.button()):
            super().mousePressEvent(event)

    def _handle_mouse_capture(self, btn) -> bool:
        """Finish capture with a mouse button. Returns True if handled."""
        mouse_key = self._MOUSE_MAP.get(btn)
        if not mouse_key:
            return False

        row = self._capturing_row
        col = self._capturing_col
        self._capturing_row = -1
        self._capturing_col = -1
        self._capture_label.setText("")

        display = MOUSE_BUTTON_NAMES.get(mouse_key, mouse_key)
        self.table.item(row, col).setText(display)
        field = _HOTKEY_DEFS[row][0]
        binding: HotkeyBinding = getattr(self._config, field)
        if col == 1:
            binding.key = mouse_key
        else:
            binding.secondary_key = mouse_key
        self.hotkeys_changed.emit(self._config)
        return True

    def _reset(self):
        self._config = HotkeyConfig()
        for row in range(self.table.rowCount()):
            self.table.removeCellWidget(row, 3)
        self._load()
        self.hotkeys_changed.emit(self._config)
        self._capture_label.setText("Defaults restored")

    def get_config(self) -> HotkeyConfig:
        return self._config


def _qt_key_to_name(key: int) -> str:
    _special = {
        Qt.Key.Key_F1: "f1", Qt.Key.Key_F2: "f2", Qt.Key.Key_F3: "f3",
        Qt.Key.Key_F4: "f4", Qt.Key.Key_F5: "f5", Qt.Key.Key_F6: "f6",
        Qt.Key.Key_F7: "f7", Qt.Key.Key_F8: "f8", Qt.Key.Key_F9: "f9",
        Qt.Key.Key_F10: "f10", Qt.Key.Key_F11: "f11", Qt.Key.Key_F12: "f12",
        Qt.Key.Key_Space: "space",
        Qt.Key.Key_Return: "enter", Qt.Key.Key_Enter: "enter",
        Qt.Key.Key_Tab: "tab",
        Qt.Key.Key_Escape: "esc",
        Qt.Key.Key_Backspace: "backspace",
        Qt.Key.Key_Delete: "delete",
        Qt.Key.Key_Insert: "insert",
        Qt.Key.Key_Home: "home", Qt.Key.Key_End: "end",
        Qt.Key.Key_PageUp: "page_up", Qt.Key.Key_PageDown: "page_down",
        Qt.Key.Key_Up: "up", Qt.Key.Key_Down: "down",
        Qt.Key.Key_Left: "left", Qt.Key.Key_Right: "right",
        Qt.Key.Key_CapsLock: "caps_lock",
        Qt.Key.Key_NumLock: "num_lock",
    }
    if key in _special:
        return _special[key]
    text = QKeySequence(key).toString().lower()
    if text and len(text) == 1:
        return text
    return text or ""
