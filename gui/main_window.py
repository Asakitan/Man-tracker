"""
Main application window - frameless design with custom title bar
"""
import sys
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QSplitter, QStatusBar, QLabel,
    QPushButton, QMessageBox, QApplication, QFileDialog, QMenu,
)
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QIcon

from config import AppConfig, SkeletonPoint, SKELETON_POINT_CN
from utils.obfuscation import _s
from utils.resource_path import config_dir

from .styles import DARK_STYLE
from .video_widget import VideoWidget
from .skeleton_widget import SkeletonWidget
from .settings_panel import SettingsPanel
from .hotkey_editor import HotkeyEditor
from .worker_thread import ProcessingThread
from .hotkey_listener import HotkeyListener


_CONFIG_PATH = os.path.join(config_dir(), "config_user.json")


# ────────────────── Custom Title Bar ──────────────────

class _TitleBar(QWidget):
    """Custom draggable title bar for frameless window"""

    minimize_clicked = pyqtSignal()
    close_clicked = pyqtSignal()
    hide_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setObjectName("titleBar")
        self._drag_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 4, 0)
        layout.setSpacing(4)

        self._title = QLabel("")
        self._title.setStyleSheet("color: #6c7086; font-size: 12px;")
        layout.addWidget(self._title)
        layout.addStretch()

        # Hide button
        self.btn_hide = QPushButton("━")
        self.btn_hide.setObjectName("titleBtn")
        self.btn_hide.setFixedSize(36, 28)
        self.btn_hide.setToolTip("F8")
        self.btn_hide.clicked.connect(self.hide_clicked.emit)
        layout.addWidget(self.btn_hide)

        # Minimize button
        self.btn_min = QPushButton("─")
        self.btn_min.setObjectName("titleBtn")
        self.btn_min.setFixedSize(36, 28)
        self.btn_min.clicked.connect(self.minimize_clicked.emit)
        layout.addWidget(self.btn_min)

        # Close button
        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("titleCloseBtn")
        self.btn_close.setFixedSize(36, 28)
        self.btn_close.clicked.connect(self.close_clicked.emit)
        layout.addWidget(self.btn_close)

    def set_title(self, text: str):
        self._title.setText(text)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            win = self.window()
            if win.isMaximized():
                win.showNormal()
            else:
                win.showMaximized()


_TITLE_BAR_STYLE = """
#titleBar {
    background-color: #11111b;
    border-bottom: 1px solid #313244;
}
#titleBtn {
    background-color: transparent;
    color: #6c7086;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    font-weight: bold;
    padding: 0px;
    min-height: 0px;
}
#titleBtn:hover {
    background-color: #313244;
    color: #cdd6f4;
}
#titleCloseBtn {
    background-color: transparent;
    color: #6c7086;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    font-weight: bold;
    padding: 0px;
    min-height: 0px;
}
#titleCloseBtn:hover {
    background-color: #f38ba8;
    color: #1e1e2e;
}
"""


class MainWindow(QMainWindow):

    _toggle_visibility_signal = pyqtSignal()

    def __init__(self, config: Optional[AppConfig] = None):
        super().__init__()
        self.config = config or self._load_or_default()
        self._worker: Optional[ProcessingThread] = None
        self._hotkey_listener: Optional[HotkeyListener] = None

        # Frameless window, always on top
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self.resize(1280, 780)
        self.setMinimumSize(960, 600)

        self._build_ui()
        self._build_statusbar()
        self._connect_signals()

        self.setStyleSheet(DARK_STYLE + _TITLE_BAR_STYLE)

        # Global visibility hotkey (Ctrl+Shift+H)
        self._toggle_visibility_signal.connect(self._toggle_visibility)
        self._setup_visibility_hotkey()

    # ================================================================
    #  Visibility Hotkey
    # ================================================================

    def _setup_visibility_hotkey(self):
        # Visibility is now handled through the main hotkey listener
        # via toggle_visibility binding (default F8).
        # We still keep a dedicated global listener as fallback for
        # when the main listener is not running (before tracking starts).
        try:
            from pynput import keyboard, mouse

            self._vis_kb_listener = keyboard.Listener(
                on_press=self._vis_on_key_press,
                on_release=self._vis_on_key_release,
            )
            self._vis_kb_listener.daemon = True
            self._vis_kb_listener.start()

            self._vis_mouse_listener = mouse.Listener(
                on_click=self._vis_on_mouse_click,
            )
            self._vis_mouse_listener.daemon = True
            self._vis_mouse_listener.start()

            self._vis_pressed: set = set()
        except Exception:
            self._vis_kb_listener = None
            self._vis_mouse_listener = None
            self._vis_pressed = set()

    def _vis_check_binding(self, key_name: str, pressed: bool):
        """Check if the visibility hotkey combo is satisfied."""
        if pressed:
            self._vis_pressed.add(key_name.lower())
        else:
            self._vis_pressed.discard(key_name.lower())
            return  # only trigger on press

        binding = self.config.hotkeys.toggle_visibility
        primary = binding.key.lower()
        secondary = getattr(binding, 'secondary_key', '').lower()

        if secondary:
            if primary in self._vis_pressed and secondary in self._vis_pressed:
                self._toggle_visibility_signal.emit()
        else:
            if key_name.lower() == primary:
                self._toggle_visibility_signal.emit()

    def _vis_on_key_press(self, key):
        try:
            from gui.hotkey_listener import _normalize_key
            name = _normalize_key(key)
            if name:
                self._vis_check_binding(name, True)
        except Exception:
            pass

    def _vis_on_key_release(self, key):
        try:
            from gui.hotkey_listener import _normalize_key
            name = _normalize_key(key)
            if name:
                self._vis_check_binding(name, False)
        except Exception:
            pass

    def _vis_on_mouse_click(self, x, y, button, pressed):
        try:
            from gui.hotkey_listener import _normalize_mouse_button
            name = _normalize_mouse_button(button)
            if name:
                self._vis_check_binding(name, pressed)
        except Exception:
            pass

    def _toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            self.show()  # re-show required after setWindowFlags
            self.activateWindow()
            self.raise_()

    # ================================================================
    #  UI Build
    # ================================================================

    def _build_ui(self):
        main_wrapper = QWidget()
        self.setCentralWidget(main_wrapper)
        main_layout = QVBoxLayout(main_wrapper)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Custom title bar
        self._title_bar = _TitleBar(self)
        self._title_bar.close_clicked.connect(self.close)
        self._title_bar.minimize_clicked.connect(self.showMinimized)
        self._title_bar.hide_clicked.connect(self.hide)
        main_layout.addWidget(self._title_bar)

        # Content area
        content = QWidget()
        root_lay = QHBoxLayout(content)
        root_lay.setContentsMargins(6, 6, 6, 6)
        root_lay.setSpacing(6)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Video + Controls
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)

        self.video_widget = VideoWidget()
        left_lay.addWidget(self.video_widget, stretch=1)

        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(10)

        self.btn_start = QPushButton(_s("start"))
        self.btn_start.setObjectName("startBtn")
        self.btn_stop = QPushButton(_s("stop"))
        self.btn_stop.setObjectName("stopBtn")
        self.btn_stop.setEnabled(False)

        ctrl_bar.addStretch()
        ctrl_bar.addWidget(self.btn_start)
        ctrl_bar.addWidget(self.btn_stop)
        ctrl_bar.addStretch()

        left_lay.addLayout(ctrl_bar)
        splitter.addWidget(left)

        # Right: Tabs
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()

        self.settings_panel = SettingsPanel(self.config)
        self.tabs.addTab(self.settings_panel, _s("tab_settings"))

        skeleton_tab = QWidget()
        skel_lay = QVBoxLayout(skeleton_tab)
        skel_title = QLabel(_s("skel_tip"))
        skel_title.setObjectName("subtitleLabel")
        skel_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        skel_lay.addWidget(skel_title)
        self.skeleton_widget = SkeletonWidget()
        self.skeleton_widget.set_selected(self.config.mouse.target_skeleton_point)
        skel_lay.addWidget(self.skeleton_widget, stretch=1)
        self.lbl_skel_info = QLabel(self._skel_info_text())
        self.lbl_skel_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_skel_info.setWordWrap(True)
        skel_lay.addWidget(self.lbl_skel_info)
        self.tabs.addTab(skeleton_tab, _s("tab_skeleton"))

        self.hotkey_editor = HotkeyEditor(self.config.hotkeys)
        self.tabs.addTab(self.hotkey_editor, _s("tab_hotkey"))

        right_lay.addWidget(self.tabs)
        right.setMinimumWidth(380)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([750, 450])

        root_lay.addWidget(splitter)
        main_layout.addWidget(content, stretch=1)

    def _build_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.lbl_fps = QLabel(_s("fps_default"))
        self.lbl_tracks = QLabel(_s("track_zero"))
        self.lbl_point = QLabel(
            _s("skelpt") + SKELETON_POINT_CN.get(self.config.mouse.target_skeleton_point, '')
        )
        self.lbl_mouse = QLabel(
            _s("mouse_on") if self.config.mouse.enable_mouse_control else _s("mouse_off")
        )
        self.lbl_state = QLabel(_s("state_ready"))
        self.lbl_state.setStyleSheet("color: #a6adc8;")

        for w in (self.lbl_state, self.lbl_fps, self.lbl_tracks, self.lbl_point, self.lbl_mouse):
            self.status_bar.addPermanentWidget(w)

    # ================================================================
    #  Signals
    # ================================================================

    def _connect_signals(self):
        self.btn_start.clicked.connect(self._start_tracking)
        self.btn_stop.clicked.connect(self._stop_tracking)

        self.skeleton_widget.point_selected.connect(self._on_skeleton_selected)

        self.settings_panel.smoothing_changed.connect(self._on_smoothing)
        self.settings_panel.speed_changed.connect(self._on_speed)
        self.settings_panel.mouse_toggled.connect(self._on_mouse_toggled)
        self.settings_panel.target_id_changed.connect(self._on_target_id)
        self.settings_panel.auto_click_toggled.connect(self._on_auto_click_toggled)

        self.settings_panel.kmbox_connect_requested.connect(self._on_kmbox_connect)
        self.settings_panel.kmbox_disconnect_requested.connect(self._on_kmbox_disconnect)

        self.hotkey_editor.hotkeys_changed.connect(self._on_hotkeys_changed)

    # ================================================================
    #  Tracking
    # ================================================================

    def _start_tracking(self):
        self.settings_panel.apply_to_config(self.config)
        self.config.mouse.target_skeleton_point = self.skeleton_widget.selected_point()
        self.config.hotkeys = self.hotkey_editor.get_config()

        source_type = self.settings_panel.get_source_type()
        source_kwargs = self.settings_panel.get_source_kwargs()

        if source_type == "file":
            source = source_kwargs.get("source", "")
            if not source:
                QMessageBox.warning(self, _s("hint"), _s("warn_source"))
                return
            self.config.video.source = source
        elif source_type == "window":
            if not source_kwargs.get("hwnd"):
                QMessageBox.warning(self, _s("hint"), _s("warn_window"))
                return

        self.config.video.show_preview = False

        self._worker = ProcessingThread(
            self.config,
            source_type=source_type,
            source_kwargs=source_kwargs,
        )
        self._worker.frame_ready.connect(self.video_widget.update_frame)
        self._worker.stats_updated.connect(self._update_stats)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.finished_clean.connect(self._on_finished)
        self._worker.model_loaded.connect(self._on_model_loaded)

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.lbl_state.setText(_s("state_loading"))
        self.lbl_state.setStyleSheet("color: #f9e2af;")

        # Hold mode: start paused, wait for hotkey press to activate
        if self.config.hotkeys.toggle_tracking.mode == "hold":
            self._worker.set_paused(True)

        self._worker.start()

        # Initialize hotkey listener with current toggle states from UI
        # This ensures HotkeyListener's internal state matches actual checkbox states
        initial_toggle_states = {
            "toggle_auto_click": self.settings_panel.chk_auto_click.isChecked(),
        }
        self._hotkey_listener = HotkeyListener(self.config.hotkeys, initial_toggle_states)
        self._hotkey_listener.action_triggered.connect(self._on_hotkey_action)
        self._hotkey_listener.start()

    def _stop_tracking(self):
        if self._hotkey_listener:
            self._hotkey_listener.stop()
            self._hotkey_listener = None
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(5000)
        self._cleanup_ui()

    # ---- Runtime params ----

    def _on_skeleton_selected(self, point: SkeletonPoint):
        self.config.mouse.target_skeleton_point = point
        self.lbl_skel_info.setText(self._skel_info_text())
        self.lbl_point.setText(_s("skelpt") + SKELETON_POINT_CN.get(point, point.name))
        if self._worker:
            self._worker.set_skeleton_point(point)

    def _on_smoothing(self, v: float):
        if self._worker:
            self._worker.set_smoothing(v)

    def _on_speed(self, v: float):
        if self._worker:
            self._worker.set_speed(v)

    def _on_mouse_toggled(self, enabled: bool):
        self.lbl_mouse.setText(_s("mouse_on") if enabled else _s("mouse_off"))
        if self._worker:
            self._worker.set_mouse_enabled(enabled)

    def _on_hotkeys_changed(self, config):
        if self._hotkey_listener:
            self._hotkey_listener.update_config(config)

    def _on_target_id(self, tid):
        if self._worker:
            self._worker.set_target_id(tid)

    def _on_auto_click_toggled(self, enabled: bool):
        if self._worker:
            self._worker.set_auto_click_enabled(enabled)

    # ---- KMBOX ----

    def _on_kmbox_connect(self):
        km_cfg = self.settings_panel.get_kmbox_config()
        try:
            from core.kmbox_net import KmboxNetDevice, KmboxConfig as DevCfg
            dev_cfg = DevCfg(
                enabled=True, ip=km_cfg.ip,
                port=km_cfg.port, mac=km_cfg.mac, timeout=km_cfg.timeout,
            )
            dev = KmboxNetDevice(dev_cfg)
            ok = dev.connect()
            if ok:
                dev.close()
                # Save KMBOX settings into app config so the worker uses them
                self.config.kmbox.enabled = True
                self.config.kmbox.ip = km_cfg.ip
                self.config.kmbox.port = km_cfg.port
                self.config.kmbox.mac = km_cfg.mac
                self.config.kmbox.timeout = km_cfg.timeout
                self.settings_panel.set_kmbox_status(True)
                self.statusBar().showMessage(_s("kmbox_ok"), 3000)
            else:
                self.settings_panel.set_kmbox_status(False)
                self.statusBar().showMessage(_s("kmbox_fail"), 3000)
        except Exception as e:
            self.settings_panel.set_kmbox_status(False)
            self.statusBar().showMessage(_s("kmbox_err") + str(e), 5000)

    def _on_kmbox_disconnect(self):
        self.config.kmbox.enabled = False
        self.settings_panel.set_kmbox_status(False)
        self.statusBar().showMessage(_s("kmbox_disc"), 2000)

    # ---- Hotkey Actions ----

    def _on_hotkey_action(self, action: str, activated: bool):
        if action == "toggle_tracking":
            if self._worker:
                binding = self.config.hotkeys.toggle_tracking
                if binding.mode == "hold":
                    self._worker.set_paused(not activated)
                    paused = self._worker.is_paused
                    self.lbl_state.setText(
                        _s("state_paused") if paused else _s("state_running")
                    )
                    self.lbl_state.setStyleSheet(
                        "color: #f9e2af;" if paused else "color: #a6e3a1;"
                    )
                elif binding.mode == "toggle" and activated:
                    if self._worker:
                        self._worker.toggle_pause()
                        paused = self._worker.is_paused
                        self.lbl_state.setText(
                            _s("state_paused") if paused else _s("state_running")
                        )
                        self.lbl_state.setStyleSheet(
                            "color: #f9e2af;" if paused else "color: #a6e3a1;"
                        )
        elif action == "toggle_auto_click":
            if self._worker:
                # Use activated state from HotkeyListener (now properly synced with initial UI state)
                self._worker.set_auto_click_enabled(activated)
                self.settings_panel.chk_auto_click.setChecked(activated)
        elif action == "toggle_visibility":
            if activated:
                self._toggle_visibility_signal.emit()
        elif action == "quit":
            if activated:
                self._stop_tracking()
                self.close()
        elif action == "increase_smoothing":
            if activated:
                v = min(self.settings_panel.sld_smooth.value() + 5, 100)
                self.settings_panel.sld_smooth.setValue(v)
        elif action == "decrease_smoothing":
            if activated:
                v = max(self.settings_panel.sld_smooth.value() - 5, 10)
                self.settings_panel.sld_smooth.setValue(v)
        elif action == "increase_speed":
            if activated:
                v = min(self.settings_panel.sld_speed.value() + 10, 300)
                self.settings_panel.sld_speed.setValue(v)
        elif action == "decrease_speed":
            if activated:
                v = max(self.settings_panel.sld_speed.value() - 10, 10)
                self.settings_panel.sld_speed.setValue(v)

    # ---- Worker Callbacks ----

    def _on_model_loaded(self):
        if self._worker and self._worker.is_paused:
            self.lbl_state.setText(_s("state_hold"))
            self.lbl_state.setStyleSheet("color: #f9e2af;")
        else:
            self.lbl_state.setText(_s("state_running"))
            self.lbl_state.setStyleSheet("color: #a6e3a1;")

    def _update_stats(self, stats: dict):
        self.lbl_fps.setText(f"FPS: {stats.get('fps', 0):.1f}")
        self.lbl_tracks.setText(f"Track: {stats.get('track_count', 0)}")
        pt_name = stats.get("target_point", "")
        sp = getattr(SkeletonPoint, pt_name, None)
        if sp:
            self.lbl_point.setText(_s("skelpt") + SKELETON_POINT_CN.get(sp, pt_name))
        backend = stats.get("mouse_backend", "")
        if backend:
            self.lbl_mouse.setText(f"Mouse: {backend}")

    def _on_error(self, msg: str):
        self._cleanup_ui()
        QMessageBox.critical(self, _s("err_title"), msg)

    def _on_finished(self):
        self._cleanup_ui()
        self.lbl_state.setText(_s("state_done"))
        self.lbl_state.setStyleSheet("color: #89b4fa;")

    def _cleanup_ui(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.video_widget.clear_view()
        if self.lbl_state.text() != _s("state_done"):
            self.lbl_state.setText(_s("state_ready"))
            self.lbl_state.setStyleSheet("color: #a6adc8;")

    # ================================================================
    #  Config
    # ================================================================

    def _save_config(self):
        self.settings_panel.apply_to_config(self.config)
        self.config.mouse.target_skeleton_point = self.skeleton_widget.selected_point()
        self.config.hotkeys = self.hotkey_editor.get_config()
        try:
            self.config.save(_CONFIG_PATH)
            self.status_bar.showMessage(_s("cfg_saved"), 3000)
        except Exception as e:
            QMessageBox.warning(self, _s("save_fail"), str(e))

    def _load_config_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, _s("load_cfg"), "", _s("json_filter")
        )
        if path:
            try:
                self.config = AppConfig.load(path)
                self.status_bar.showMessage(_s("loaded") + path, 3000)
            except Exception as e:
                QMessageBox.warning(self, _s("load_fail"), str(e))

    @staticmethod
    def _load_or_default() -> AppConfig:
        if os.path.isfile(_CONFIG_PATH):
            try:
                return AppConfig.load(_CONFIG_PATH)
            except Exception:
                pass
        return AppConfig()

    # ================================================================
    #  Helpers
    # ================================================================

    def _skel_info_text(self) -> str:
        sp = self.skeleton_widget.selected_point()
        cn = SKELETON_POINT_CN.get(sp, sp.name)
        return f'{_s("cur_sel")}<b style="color:#f38ba8;">{cn}</b>  ({sp.name})'

    def _show_about(self):
        QMessageBox.about(
            self, _s("about_title"),
            "<h3>Application</h3><p>Detection + Tracking + Control + GUI</p>"
        )

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(DARK_STYLE)
        act_save = menu.addAction(_s("menu_save"))
        act_save.triggered.connect(self._save_config)
        act_load = menu.addAction(_s("menu_load"))
        act_load.triggered.connect(self._load_config_dialog)
        menu.addSeparator()
        act_about = menu.addAction(_s("menu_about"))
        act_about.triggered.connect(self._show_about)
        menu.addSeparator()
        act_exit = menu.addAction(_s("menu_exit"))
        act_exit.triggered.connect(self.close)
        menu.exec(event.globalPos())

    def closeEvent(self, event):  # noqa: N802
        # Stop visibility listeners
        for attr in ('_vis_kb_listener', '_vis_mouse_listener'):
            listener = getattr(self, attr, None)
            if listener:
                try:
                    listener.stop()
                except Exception:
                    pass
        if self._hotkey_listener:
            self._hotkey_listener.stop()
            self._hotkey_listener = None
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(3000)
        try:
            self.settings_panel.apply_to_config(self.config)
            self.config.save(_CONFIG_PATH)
        except Exception:
            pass
        event.accept()
