"""
Settings panel
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLabel, QSlider, QComboBox,
    QCheckBox, QDoubleSpinBox, QSpinBox, QPushButton,
    QFileDialog, QLineEdit, QStackedWidget, QDialog,
    QDialogButtonBox, QListWidget, QListWidgetItem,
    QApplication, QRubberBand, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint, QSize
from PyQt6.QtGui import QScreen

from config import AppConfig, SkeletonPoint, SKELETON_POINT_CN, KmboxConfig
from utils.obfuscation import _s


def _make_slider(min_v: int, max_v: int, value: int, tick: int = 1) -> QSlider:
    s = QSlider(Qt.Orientation.Horizontal)
    s.setRange(min_v, max_v)
    s.setValue(value)
    s.setTickInterval(tick)
    return s


class SettingsPanel(QWidget):
    """Settings panel"""

    # real-time parameter change signals
    smoothing_changed = pyqtSignal(float)
    speed_changed = pyqtSignal(float)
    skeleton_changed = pyqtSignal(object)  # SkeletonPoint
    mouse_toggled = pyqtSignal(bool)
    conf_changed = pyqtSignal(float)
    target_id_changed = pyqtSignal(object)  # int | None
    auto_click_toggled = pyqtSignal(bool)          # auto-click toggle
    kmbox_connect_requested = pyqtSignal()     # request KMBOX connect
    kmbox_disconnect_requested = pyqtSignal()  # request KMBOX disconnect

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._init_ui()

    # ================================================================
    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # wrap all content in ScrollArea to prevent clipping
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        # ---------- Video Source ----------
        grp_src = QGroupBox(_s("src_group"))
        lay_src = QVBoxLayout(grp_src)

        # Source type
        row_type = QHBoxLayout()
        row_type.addWidget(QLabel(_s("src_type")))
        self.cmb_source_type = QComboBox()
        self.cmb_source_type.addItems([_s("src_file"), _s("src_screen"), _s("src_window")])
        self.cmb_source_type.currentIndexChanged.connect(self._on_source_type_changed)
        row_type.addWidget(self.cmb_source_type, stretch=1)
        lay_src.addLayout(row_type)

        # -- stacked pages --
        self.source_stack = QStackedWidget()

        # page 0: video file / camera
        page_file = QWidget()
        lay_file = QVBoxLayout(page_file)
        lay_file.setContentsMargins(0, 4, 0, 0)
        row_src = QHBoxLayout()
        self.txt_source = QLineEdit(self.config.video.source or "0")
        self.txt_source.setPlaceholderText(_s("src_placeholder"))
        self.btn_browse = QPushButton(_s("browse"))
        self.btn_browse.setFixedWidth(80)
        self.btn_browse.clicked.connect(self._browse_video)
        row_src.addWidget(self.txt_source)
        row_src.addWidget(self.btn_browse)
        lay_file.addLayout(row_src)
        self.source_stack.addWidget(page_file)

        # page 1: screen region
        page_screen = QWidget()
        lay_screen = QVBoxLayout(page_screen)
        lay_screen.setContentsMargins(0, 4, 0, 0)

        row_region = QHBoxLayout()
        self.lbl_region = QLabel(_s("fullscreen"))
        self.lbl_region.setStyleSheet("color: #a6adc8;")
        self.btn_select_region = QPushButton(_s("sel_region"))
        self.btn_select_region.clicked.connect(self._select_screen_region)
        self.btn_fullscreen = QPushButton(_s("fullscr_btn"))
        self.btn_fullscreen.setFixedWidth(55)
        self.btn_fullscreen.clicked.connect(self._set_fullscreen_region)
        row_region.addWidget(self.lbl_region, stretch=1)
        row_region.addWidget(self.btn_fullscreen)
        row_region.addWidget(self.btn_select_region)
        lay_screen.addLayout(row_region)

        row_fps_scr = QHBoxLayout()
        row_fps_scr.addWidget(QLabel(_s("cap_fps")))
        self.spn_screen_fps = QSpinBox()
        self.spn_screen_fps.setRange(1, 120)
        self.spn_screen_fps.setValue(30)
        self.spn_screen_fps.setSuffix(" fps")
        row_fps_scr.addWidget(self.spn_screen_fps)
        row_fps_scr.addStretch()
        lay_screen.addLayout(row_fps_scr)

        self.source_stack.addWidget(page_screen)

        # page 2: window capture
        page_window = QWidget()
        lay_window = QVBoxLayout(page_window)
        lay_window.setContentsMargins(0, 4, 0, 0)

        row_win = QHBoxLayout()
        self.cmb_window = QComboBox()
        self.cmb_window.setMinimumWidth(200)
        self.btn_refresh_windows = QPushButton(_s("refresh"))
        self.btn_refresh_windows.setFixedWidth(55)
        self.btn_refresh_windows.clicked.connect(self._refresh_windows)
        row_win.addWidget(self.cmb_window, stretch=1)
        row_win.addWidget(self.btn_refresh_windows)
        lay_window.addLayout(row_win)

        row_fps_win = QHBoxLayout()
        row_fps_win.addWidget(QLabel(_s("cap_fps")))
        self.spn_window_fps = QSpinBox()
        self.spn_window_fps.setRange(1, 120)
        self.spn_window_fps.setValue(30)
        self.spn_window_fps.setSuffix(" fps")
        row_fps_win.addWidget(self.spn_window_fps)
        row_fps_win.addStretch()
        lay_window.addLayout(row_fps_win)

        self.source_stack.addWidget(page_window)

        lay_src.addWidget(self.source_stack)

        # -- output saving (common to all sources) --
        row_out = QHBoxLayout()
        self.chk_save = QCheckBox(_s("save_output"))
        self.chk_save.setChecked(self.config.video.save_video)
        self.txt_output = QLineEdit(self.config.video.output_path or "")
        self.txt_output.setPlaceholderText(_s("output_path"))
        self.btn_browse_out = QPushButton(_s("browse"))
        self.btn_browse_out.setFixedWidth(80)
        self.btn_browse_out.clicked.connect(self._browse_output)
        row_out.addWidget(self.chk_save)
        row_out.addWidget(self.txt_output)
        row_out.addWidget(self.btn_browse_out)
        lay_src.addLayout(row_out)

        root.addWidget(grp_src)

        # store region / window selection state
        self._screen_region = None     # (left, top, width, height) or None=fullscreen
        self._selected_hwnd = None     # window handle
        self._window_list = []         # [{hwnd, title, rect}, ...]

        # initialise window list
        self._refresh_windows()

        # ── restore saved source settings ──
        _src_type_map = {"file": 0, "screen": 1, "window": 2}
        saved_idx = _src_type_map.get(self.config.video.source_type, 0)
        self.cmb_source_type.setCurrentIndex(saved_idx)

        # restore screen region
        sr = self.config.video.screen_region
        if sr is not None and len(sr) == 4:
            self._screen_region = tuple(sr)
            self.lbl_region.setText(f"({sr[0]}, {sr[1]}) {sr[2]}×{sr[3]}")

        # restore screen fps
        self.spn_screen_fps.setValue(self.config.video.screen_fps)

        # restore window fps
        self.spn_window_fps.setValue(self.config.video.window_fps)

        # restore window selection by title
        if self.config.video.window_title:
            for i, info in enumerate(self._window_list):
                if info["title"] == self.config.video.window_title:
                    self.cmb_window.setCurrentIndex(i)
                    break

        # ---------- Model & Device ----------
        grp_model = QGroupBox(_s("model_group"))
        form_model = QFormLayout(grp_model)

        self.cmb_model = QComboBox()
        self.cmb_model.addItems([
            "model-pose-n.pt",
            "model-pose-s.pt",
            "model-pose-m.pt",
            "model-pose-l.pt",
            "model-pose-x.pt",
        ])
        self.cmb_model.setCurrentText(self.config.detector.model_path)
        self.cmb_model.setEditable(True)
        form_model.addRow(_s("model_label"), self.cmb_model)

        self.cmb_device = QComboBox()
        self.cmb_device.addItems(["auto", "cuda", "cpu"])
        self.cmb_device.setCurrentText(self.config.detector.device)
        form_model.addRow(_s("device_label"), self.cmb_device)

        self.spn_imgsz = QComboBox()
        self.spn_imgsz.addItems(["320", "416", "480", "640", "800", "1024"])
        self.spn_imgsz.setCurrentText(str(self.config.detector.imgsz))
        form_model.addRow(_s("imgsz_label"), self.spn_imgsz)

        self.chk_half = QCheckBox(_s("fp16"))
        self.chk_half.setChecked(self.config.detector.half_precision)
        form_model.addRow(self.chk_half)

        self.spn_detect_interval = QSpinBox()
        self.spn_detect_interval.setRange(1, 10)
        self.spn_detect_interval.setValue(self.config.detector.detect_interval)
        self.spn_detect_interval.setToolTip(_s("det_tip"))
        form_model.addRow(_s("det_interval"), self.spn_detect_interval)

        root.addWidget(grp_model)

        # ---------- Detection ----------
        grp_det = QGroupBox(_s("det_group"))
        lay_det = QVBoxLayout(grp_det)

        # confidence threshold
        row_conf = QHBoxLayout()
        row_conf.addWidget(QLabel(_s("conf_label")))
        self.sld_conf = _make_slider(10, 95, int(self.config.detector.conf_threshold * 100))
        self.lbl_conf = QLabel(f"{self.config.detector.conf_threshold:.2f}")
        self.lbl_conf.setObjectName("valueLabel")
        self.sld_conf.valueChanged.connect(
            lambda v: (
                self.lbl_conf.setText(f"{v / 100:.2f}"),
                self.conf_changed.emit(v / 100),
            )
        )
        row_conf.addWidget(self.sld_conf)
        row_conf.addWidget(self.lbl_conf)
        lay_det.addLayout(row_conf)

        # processing scale
        row_scale = QHBoxLayout()
        row_scale.addWidget(QLabel(_s("scale_label")))
        self.sld_scale = _make_slider(25, 100, int(self.config.video.process_scale * 100))
        self.lbl_scale = QLabel(f"{self.config.video.process_scale:.0%}")
        self.lbl_scale.setObjectName("valueLabel")
        self.sld_scale.valueChanged.connect(
            lambda v: self.lbl_scale.setText(f"{v}%")
        )
        row_scale.addWidget(self.sld_scale)
        row_scale.addWidget(self.lbl_scale)
        lay_det.addLayout(row_scale)

        # red edge glow suppression
        self.chk_red_filter = QCheckBox(_s("red_filter"))
        self.chk_red_filter.setChecked(self.config.detector.red_edge_filter)
        self.chk_red_filter.setToolTip(_s("red_filter_tip"))
        lay_det.addWidget(self.chk_red_filter)

        root.addWidget(grp_det)

        # ---------- Mouse Control ----------
        grp_mouse = QGroupBox(_s("mouse_group"))
        lay_mouse = QVBoxLayout(grp_mouse)

        self.chk_mouse = QCheckBox(_s("mouse_enable"))
        self.chk_mouse.setChecked(self.config.mouse.enable_mouse_control)
        self.chk_mouse.toggled.connect(self.mouse_toggled.emit)
        lay_mouse.addWidget(self.chk_mouse)

        # smoothing factor
        row_smooth = QHBoxLayout()
        row_smooth.addWidget(QLabel(_s("smooth_label")))
        self.sld_smooth = _make_slider(10, 100, int(self.config.mouse.smoothing_factor * 10))
        self.lbl_smooth = QLabel(f"{self.config.mouse.smoothing_factor:.1f}")
        self.lbl_smooth.setObjectName("valueLabel")
        self.sld_smooth.valueChanged.connect(
            lambda v: (
                self.lbl_smooth.setText(f"{v / 10:.1f}"),
                self.smoothing_changed.emit(v / 10),
            )
        )
        row_smooth.addWidget(self.sld_smooth)
        row_smooth.addWidget(self.lbl_smooth)
        lay_mouse.addLayout(row_smooth)

        # mouse speed
        row_speed = QHBoxLayout()
        row_speed.addWidget(QLabel(_s("speed_label")))
        self.sld_speed = _make_slider(10, 300, int(self.config.mouse.mouse_speed * 100))
        self.lbl_speed = QLabel(f"{self.config.mouse.mouse_speed:.1f}x")
        self.lbl_speed.setObjectName("valueLabel")
        self.sld_speed.valueChanged.connect(
            lambda v: (
                self.lbl_speed.setText(f"{v / 100:.1f}x"),
                self.speed_changed.emit(v / 100),
            )
        )
        row_speed.addWidget(self.sld_speed)
        row_speed.addWidget(self.lbl_speed)
        lay_mouse.addLayout(row_speed)

        # coordinate mapping
        row_map = QHBoxLayout()
        row_map.addWidget(QLabel(_s("map_label")))
        self.cmb_mapping = QComboBox()
        self.cmb_mapping.addItems(["relative", "absolute"])
        self.cmb_mapping.setCurrentText(self.config.mouse.coordinate_mapping)
        row_map.addWidget(self.cmb_mapping)
        lay_mouse.addLayout(row_map)

        # target ID
        row_tid = QHBoxLayout()
        row_tid.addWidget(QLabel(_s("tid_label")))
        self.spn_tid = QSpinBox()
        self.spn_tid.setRange(-1, 99)
        self.spn_tid.setSpecialValueText(_s("auto"))
        self.spn_tid.setValue(
            self.config.mouse.target_track_id
            if self.config.mouse.target_track_id is not None
            else -1
        )
        self.spn_tid.valueChanged.connect(
            lambda v: self.target_id_changed.emit(None if v < 0 else v)
        )
        row_tid.addWidget(self.spn_tid)
        lay_mouse.addLayout(row_tid)

        # ---- auto-click on arrival ----
        self.chk_auto_click = QCheckBox("\u5230\u8fbe\u81ea\u52a8\u70b9\u51fb")
        self.chk_auto_click.setChecked(self.config.mouse.auto_click_enabled)
        self.chk_auto_click.setToolTip(
            "\u5230\u8fbe\u76ee\u6807\u540e\u81ea\u52a8\u70b9\u51fb\u5de6\u952e (50ms + \u968f\u673a10-50ms)"
        )
        self.chk_auto_click.toggled.connect(self.auto_click_toggled.emit)
        lay_mouse.addWidget(self.chk_auto_click)

        # arrival threshold
        row_threshold = QHBoxLayout()
        row_threshold.addWidget(QLabel("\u5230\u8fbe\u9608\u503c"))
        self.spn_threshold = QDoubleSpinBox()
        self.spn_threshold.setRange(1.0, 50.0)
        self.spn_threshold.setValue(self.config.mouse.arrival_threshold)
        self.spn_threshold.setSuffix(" px")
        self.spn_threshold.setSingleStep(1.0)
        row_threshold.addWidget(self.spn_threshold)
        row_threshold.addStretch()
        lay_mouse.addLayout(row_threshold)

        root.addWidget(grp_mouse)

        # ---------- KMBOX-NET ----------
        grp_kmbox = QGroupBox(_s("kmbox_group"))
        lay_kmbox = QVBoxLayout(grp_kmbox)

        row_backend = QHBoxLayout()
        row_backend.addWidget(QLabel(_s("backend_label")))
        self.cmb_backend = QComboBox()
        self.cmb_backend.addItems(["KMBOX-NET"])
        self.cmb_backend.setCurrentIndex(0)
        row_backend.addWidget(self.cmb_backend, stretch=1)
        lay_kmbox.addLayout(row_backend)

        # KMBOX parameters container
        self.kmbox_params = QWidget()
        form_km = QFormLayout(self.kmbox_params)
        form_km.setContentsMargins(0, 6, 0, 0)

        self.txt_km_ip = QLineEdit(self.config.kmbox.ip)
        self.txt_km_ip.setPlaceholderText(_s("ip_ph"))
        form_km.addRow(_s("ip_label"), self.txt_km_ip)

        self.spn_km_port = QSpinBox()
        self.spn_km_port.setRange(1, 65535)
        self.spn_km_port.setValue(self.config.kmbox.port)
        form_km.addRow(_s("port_label"), self.spn_km_port)

        self.txt_km_mac = QLineEdit(self.config.kmbox.mac)
        self.txt_km_mac.setPlaceholderText(_s("mac_ph"))
        self.txt_km_mac.setMaxLength(8)
        form_km.addRow(_s("mac_label"), self.txt_km_mac)

        lay_kmbox.addWidget(self.kmbox_params)

        # connect button + status
        row_km_conn = QHBoxLayout()
        self.btn_km_connect = QPushButton(_s("connect"))
        self.btn_km_connect.setFixedWidth(80)
        self.btn_km_connect.clicked.connect(self._on_kmbox_connect_clicked)
        self.lbl_km_status = QLabel(_s("disconnected"))
        self.lbl_km_status.setStyleSheet("color: #f38ba8;")  # red
        row_km_conn.addWidget(self.btn_km_connect)
        row_km_conn.addWidget(self.lbl_km_status, stretch=1)
        lay_kmbox.addLayout(row_km_conn)

        # KMBOX is the only backend — always visible
        self.kmbox_params.setVisible(True)
        self.btn_km_connect.setVisible(True)
        self.lbl_km_status.setVisible(True)

        root.addWidget(grp_kmbox)

        # ---------- Aim Curve (人性化追踪) ----------
        grp_curve = QGroupBox("追踪曲线")
        lay_curve = QVBoxLayout(grp_curve)

        # Curve mode
        row_cmode = QHBoxLayout()
        row_cmode.addWidget(QLabel("曲线模式"))
        self.cmb_curve_mode = QComboBox()
        self.cmb_curve_mode.addItems(["hybrid", "bezier", "missile"])
        self.cmb_curve_mode.setCurrentText(self.config.aim_curve.curve_mode)
        self.cmb_curve_mode.setToolTip("hybrid=远用导弹近用贝塞尔 | bezier=全程贝塞尔 | missile=全程导弹追踪")
        row_cmode.addWidget(self.cmb_curve_mode)
        lay_curve.addLayout(row_cmode)

        # Bezier aggression
        row_ba = QHBoxLayout()
        row_ba.addWidget(QLabel("贝塞尔弯曲"))
        self.sld_bezier_aggr = _make_slider(0, 100, int(self.config.aim_curve.bezier_aggression * 100))
        self.lbl_bezier_aggr = QLabel(f"{self.config.aim_curve.bezier_aggression:.2f}")
        self.lbl_bezier_aggr.setObjectName("valueLabel")
        self.sld_bezier_aggr.valueChanged.connect(
            lambda v: self.lbl_bezier_aggr.setText(f"{v / 100:.2f}")
        )
        row_ba.addWidget(self.sld_bezier_aggr)
        row_ba.addWidget(self.lbl_bezier_aggr)
        lay_curve.addLayout(row_ba)

        # Missile gain
        row_mg = QHBoxLayout()
        row_mg.addWidget(QLabel("导弹增益"))
        self.sld_missile_gain = _make_slider(10, 60, int(self.config.aim_curve.missile_gain * 10))
        self.lbl_missile_gain = QLabel(f"{self.config.aim_curve.missile_gain:.1f}")
        self.lbl_missile_gain.setObjectName("valueLabel")
        self.sld_missile_gain.valueChanged.connect(
            lambda v: self.lbl_missile_gain.setText(f"{v / 10:.1f}")
        )
        row_mg.addWidget(self.sld_missile_gain)
        row_mg.addWidget(self.lbl_missile_gain)
        lay_curve.addLayout(row_mg)

        # Acceleration factor
        row_af = QHBoxLayout()
        row_af.addWidget(QLabel("加速因子"))
        self.sld_accel = _make_slider(5, 100, int(self.config.aim_curve.accel_factor * 100))
        self.lbl_accel = QLabel(f"{self.config.aim_curve.accel_factor:.2f}")
        self.lbl_accel.setObjectName("valueLabel")
        self.sld_accel.valueChanged.connect(
            lambda v: self.lbl_accel.setText(f"{v / 100:.2f}")
        )
        row_af.addWidget(self.sld_accel)
        row_af.addWidget(self.lbl_accel)
        lay_curve.addLayout(row_af)

        # Max velocity
        row_mv = QHBoxLayout()
        row_mv.addWidget(QLabel("最大速度"))
        self.sld_max_vel = _make_slider(10, 300, int(self.config.aim_curve.max_velocity))
        self.lbl_max_vel = QLabel(f"{self.config.aim_curve.max_velocity:.0f}")
        self.lbl_max_vel.setObjectName("valueLabel")
        self.sld_max_vel.valueChanged.connect(
            lambda v: self.lbl_max_vel.setText(f"{v}")
        )
        row_mv.addWidget(self.sld_max_vel)
        row_mv.addWidget(self.lbl_max_vel)
        lay_curve.addLayout(row_mv)

        # Target EMA (smoothing)
        row_ema = QHBoxLayout()
        row_ema.addWidget(QLabel("目标平滑"))
        self.sld_ema = _make_slider(5, 100, int(self.config.aim_curve.target_ema_alpha * 100))
        self.lbl_ema = QLabel(f"{self.config.aim_curve.target_ema_alpha:.2f}")
        self.lbl_ema.setObjectName("valueLabel")
        self.sld_ema.valueChanged.connect(
            lambda v: self.lbl_ema.setText(f"{v / 100:.2f}")
        )
        row_ema.addWidget(self.sld_ema)
        row_ema.addWidget(self.lbl_ema)
        lay_curve.addLayout(row_ema)

        # Jitter
        row_jit = QHBoxLayout()
        row_jit.addWidget(QLabel("随机抖动"))
        self.sld_jitter = _make_slider(0, 30, int(self.config.aim_curve.jitter_amount * 10))
        self.lbl_jitter = QLabel(f"{self.config.aim_curve.jitter_amount:.1f}")
        self.lbl_jitter.setObjectName("valueLabel")
        self.sld_jitter.valueChanged.connect(
            lambda v: self.lbl_jitter.setText(f"{v / 10:.1f}")
        )
        row_jit.addWidget(self.sld_jitter)
        row_jit.addWidget(self.lbl_jitter)
        lay_curve.addLayout(row_jit)

        root.addWidget(grp_curve)

        # ---------- Visualization ----------
        grp_vis = QGroupBox(_s("vis_group"))
        lay_vis = QVBoxLayout(grp_vis)
        self.chk_skeleton = QCheckBox(_s("show_skel"))
        self.chk_skeleton.setChecked(self.config.visualization.draw_skeleton)
        self.chk_bbox = QCheckBox(_s("show_bbox"))
        self.chk_bbox.setChecked(self.config.visualization.draw_bbox)
        self.chk_tid = QCheckBox(_s("show_tid"))
        self.chk_tid.setChecked(self.config.visualization.draw_track_id)
        self.chk_target = QCheckBox(_s("show_target"))
        self.chk_target.setChecked(self.config.visualization.draw_target_point)
        for cb in (self.chk_skeleton, self.chk_bbox, self.chk_tid, self.chk_target):
            lay_vis.addWidget(cb)
        root.addWidget(grp_vis)

        root.addStretch()

        # put container into scroll area
        scroll.setWidget(container)
        outer.addWidget(scroll)

    # ---- helpers ----

    def _on_source_type_changed(self, idx: int):
        self.source_stack.setCurrentIndex(idx)

    def _on_backend_changed(self, idx: int):
        pass

    def _on_kmbox_connect_clicked(self):
        if self.btn_km_connect.text() == _s("connect"):
            self.kmbox_connect_requested.emit()
        else:
            self.kmbox_disconnect_requested.emit()

    def set_kmbox_status(self, connected: bool):
        if connected:
            self.lbl_km_status.setText(_s("connected"))
            self.lbl_km_status.setStyleSheet("color: #a6e3a1;")
            self.btn_km_connect.setText(_s("disconnect"))
        else:
            self.lbl_km_status.setText(_s("disconnected"))
            self.lbl_km_status.setStyleSheet("color: #f38ba8;")
            self.btn_km_connect.setText(_s("connect"))

    def get_kmbox_config(self) -> KmboxConfig:
        """Get current KMBOX panel configuration"""
        return KmboxConfig(
            enabled=(self.cmb_backend.currentIndex() == 1),
            ip=self.txt_km_ip.text().strip(),
            port=self.spn_km_port.value(),
            mac=self.txt_km_mac.text().strip(),
        )

    def _browse_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, _s("sel_video"), "",
            _s("vid_filter")
        )
        if path:
            self.txt_source.setText(path)

    def _browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, _s("save_video_dlg"), "",
            _s("mp4_filter")
        )
        if path:
            self.txt_output.setText(path)

    def _set_fullscreen_region(self):
        self._screen_region = None
        self.lbl_region.setText(_s("fullscreen"))

    def _select_screen_region(self):
        selector = _RegionSelector()
        if selector.exec() == QDialog.DialogCode.Accepted and selector.selected_rect:
            r = selector.selected_rect
            self._screen_region = (r.x(), r.y(), r.width(), r.height())
            self.lbl_region.setText(
                f"({r.x()}, {r.y()}) {r.width()}×{r.height()}"
            )

    def _refresh_windows(self):
        self.cmb_window.clear()
        self._window_list = []
        try:
            from utils.screen_capture import list_windows
            self._window_list = list_windows()
        except ImportError:
            self.cmb_window.addItem(_s("no_pywin32"))
            return

        if not self._window_list:
            self.cmb_window.addItem(_s("no_window"))
            return

        for info in self._window_list:
            title = info["title"]
            if len(title) > 60:
                title = title[:57] + "…"
            r = info["rect"]
            w, h = r[2] - r[0], r[3] - r[1]
            self.cmb_window.addItem(f"{title}  [{w}×{h}]")

    def get_source_type(self) -> str:
        """Return current source type: 'file', 'screen', 'window'"""
        idx = self.cmb_source_type.currentIndex()
        return ["file", "screen", "window"][idx]

    def get_source_kwargs(self) -> dict:
        """Return parameters needed to create a video source"""
        st = self.get_source_type()
        if st == "file":
            return {"source": self.txt_source.text().strip() or "0"}
        elif st == "screen":
            return {
                "region": self._screen_region,
                "target_fps": self.spn_screen_fps.value(),
            }
        elif st == "window":
            idx = self.cmb_window.currentIndex()
            if 0 <= idx < len(self._window_list):
                hwnd = self._window_list[idx]["hwnd"]
            else:
                hwnd = 0
            return {
                "hwnd": hwnd,
                "target_fps": self.spn_window_fps.value(),
            }
        return {}

    # ---- collect current values → AppConfig ----

    def apply_to_config(self, config: AppConfig):
        config.video.source = self.txt_source.text().strip()
        config.video.save_video = self.chk_save.isChecked()
        config.video.output_path = self.txt_output.text().strip() or None
        config.video.process_scale = self.sld_scale.value() / 100.0

        # source memory
        config.video.source_type = self.get_source_type()
        config.video.screen_region = self._screen_region
        config.video.screen_fps = self.spn_screen_fps.value()
        config.video.window_fps = self.spn_window_fps.value()
        # save window title for matching on next launch
        idx = self.cmb_window.currentIndex()
        if 0 <= idx < len(self._window_list):
            config.video.window_title = self._window_list[idx]["title"]
        else:
            config.video.window_title = ""

        config.detector.model_path = self.cmb_model.currentText()
        config.detector.device = self.cmb_device.currentText()
        config.detector.imgsz = int(self.spn_imgsz.currentText())
        config.detector.conf_threshold = self.sld_conf.value() / 100.0
        config.detector.half_precision = self.chk_half.isChecked()
        config.detector.detect_interval = self.spn_detect_interval.value()
        config.detector.red_edge_filter = self.chk_red_filter.isChecked()

        config.mouse.enable_mouse_control = self.chk_mouse.isChecked()
        config.mouse.smoothing_factor = self.sld_smooth.value() / 10.0
        config.mouse.mouse_speed = self.sld_speed.value() / 100.0
        config.mouse.coordinate_mapping = self.cmb_mapping.currentText()
        config.mouse.mouse_backend = "kmbox"

        config.mouse.auto_click_enabled = self.chk_auto_click.isChecked()
        config.mouse.arrival_threshold = self.spn_threshold.value()

        tid = self.spn_tid.value()
        config.mouse.target_track_id = None if tid < 0 else tid

        config.visualization.draw_skeleton = self.chk_skeleton.isChecked()
        config.visualization.draw_bbox = self.chk_bbox.isChecked()
        config.visualization.draw_track_id = self.chk_tid.isChecked()
        config.visualization.draw_target_point = self.chk_target.isChecked()

        # KMBOX-NET
        config.kmbox = self.get_kmbox_config()

        # Aim Curve
        config.aim_curve.curve_mode = self.cmb_curve_mode.currentText()
        config.aim_curve.bezier_aggression = self.sld_bezier_aggr.value() / 100.0
        config.aim_curve.missile_gain = self.sld_missile_gain.value() / 10.0
        config.aim_curve.accel_factor = self.sld_accel.value() / 100.0
        config.aim_curve.max_velocity = float(self.sld_max_vel.value())
        config.aim_curve.target_ema_alpha = self.sld_ema.value() / 100.0
        config.aim_curve.jitter_amount = self.sld_jitter.value() / 10.0


# ─────────────────── Screen Region Selector ───────────────────

class _RegionSelector(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)

        # cover the entire virtual desktop
        screen_geom = QApplication.primaryScreen().geometry()
        self.setGeometry(screen_geom)
        self.showFullScreen()

        self._origin = QPoint()
        self._rubber = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self.selected_rect: QRect | None = None

    def paintEvent(self, event):
        from PyQt6.QtGui import QPainter, QColor
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.pos()
            self._rubber.setGeometry(QRect(self._origin, QSize()))
            self._rubber.show()

    def mouseMoveEvent(self, event):
        if self._rubber.isVisible():
            self._rubber.setGeometry(QRect(self._origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._rubber.isVisible():
            rect = self._rubber.geometry()
            if rect.width() > 10 and rect.height() > 10:
                # convert to screen coordinates
                screen_pos = self.mapToGlobal(rect.topLeft())
                self.selected_rect = QRect(
                    screen_pos.x(), screen_pos.y(),
                    rect.width(), rect.height()
                )
                self.accept()
            else:
                self._rubber.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
