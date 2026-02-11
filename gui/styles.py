"""
GUI dark theme stylesheet
"""

DARK_STYLE = """
/* ===== Global ===== */
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
}

/* ===== Menu Bar ===== */
QMenuBar {
    background-color: #181825;
    border-bottom: 1px solid #313244;
    padding: 2px;
}
QMenuBar::item {
    padding: 6px 12px;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background-color: #45475a;
}
QMenu {
    background-color: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 28px 6px 12px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #45475a;
}
QMenu::separator {
    height: 1px;
    background-color: #313244;
    margin: 4px 8px;
}

/* ===== Tabs ===== */
QTabWidget::pane {
    border: 1px solid #313244;
    border-radius: 8px;
    background-color: #1e1e2e;
    top: -1px;
}
QTabBar::tab {
    background-color: #181825;
    color: #a6adc8;
    border: 1px solid #313244;
    border-bottom: none;
    padding: 8px 18px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 500;
}
QTabBar::tab:selected {
    background-color: #1e1e2e;
    color: #89b4fa;
    border-bottom: 2px solid #89b4fa;
}
QTabBar::tab:hover:!selected {
    background-color: #313244;
    color: #cdd6f4;
}

/* ===== Group Box ===== */
QGroupBox {
    font-weight: bold;
    font-size: 13px;
    color: #89b4fa;
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 18px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
}

/* ===== Buttons ===== */
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: 500;
    min-height: 18px;
}
QPushButton:hover {
    background-color: #45475a;
    border-color: #585b70;
}
QPushButton:pressed {
    background-color: #585b70;
}
QPushButton:disabled {
    background-color: #1e1e2e;
    color: #585b70;
    border-color: #313244;
}
QPushButton#startBtn {
    background-color: #a6e3a1;
    color: #1e1e2e;
    font-weight: bold;
    font-size: 14px;
    border: none;
    padding: 10px 24px;
}
QPushButton#startBtn:hover {
    background-color: #94e2d5;
}
QPushButton#startBtn:disabled {
    background-color: #45475a;
    color: #6c7086;
}
QPushButton#stopBtn {
    background-color: #f38ba8;
    color: #1e1e2e;
    font-weight: bold;
    font-size: 14px;
    border: none;
    padding: 10px 24px;
}
QPushButton#stopBtn:hover {
    background-color: #eba0ac;
}
QPushButton#stopBtn:disabled {
    background-color: #45475a;
    color: #6c7086;
}

/* ===== Sliders ===== */
QSlider::groove:horizontal {
    height: 6px;
    background-color: #313244;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    width: 18px;
    height: 18px;
    margin: -6px 0;
    background-color: #89b4fa;
    border-radius: 9px;
    border: 2px solid #1e1e2e;
}
QSlider::handle:horizontal:hover {
    background-color: #74c7ec;
}
QSlider::sub-page:horizontal {
    background-color: #89b4fa;
    border-radius: 3px;
}

/* ===== Combo Box ===== */
QComboBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 12px;
    min-height: 18px;
}
QComboBox:hover {
    border-color: #89b4fa;
}
QComboBox::drop-down {
    border: none;
    width: 28px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #89b4fa;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 6px;
    selection-background-color: #45475a;
    selection-color: #cdd6f4;
    padding: 4px;
}

/* ===== Table Inline Combo Box ===== */
QTableWidget QComboBox {
    padding: 2px 6px;
    border-radius: 4px;
    min-height: 14px;
}
QTableWidget QComboBox::drop-down {
    width: 22px;
}
QTableWidget QComboBox::down-arrow {
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #89b4fa;
    margin-right: 4px;
}

/* ===== Input / SpinBox ===== */
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #89b4fa;
    selection-color: #1e1e2e;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #89b4fa;
}

/* ===== Checkbox ===== */
QCheckBox {
    spacing: 8px;
    color: #cdd6f4;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #45475a;
    background-color: #313244;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}
QCheckBox::indicator:hover {
    border-color: #89b4fa;
}

/* ===== Labels ===== */
QLabel {
    color: #cdd6f4;
}
QLabel#titleLabel {
    font-size: 18px;
    font-weight: bold;
    color: #89b4fa;
}
QLabel#subtitleLabel {
    font-size: 11px;
    color: #6c7086;
}
QLabel#valueLabel {
    color: #a6e3a1;
    font-weight: bold;
    font-size: 14px;
    min-width: 45px;
}

/* ===== Status Bar ===== */
QStatusBar {
    background-color: #181825;
    border-top: 1px solid #313244;
    color: #a6adc8;
    font-size: 12px;
    padding: 2px;
}
QStatusBar QLabel {
    padding: 0 8px;
}

/* ===== Table (Hotkey Editor) ===== */
QTableWidget {
    background-color: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 6px;
    gridline-color: #313244;
    selection-background-color: #313244;
    selection-color: #cdd6f4;
}
QTableWidget::item {
    padding: 6px 10px;
    border-bottom: 1px solid #313244;
}
QTableWidget::item:selected {
    background-color: #313244;
}
QHeaderView::section {
    background-color: #181825;
    color: #89b4fa;
    border: none;
    border-bottom: 2px solid #313244;
    padding: 8px 12px;
    font-weight: bold;
}

/* ===== Scrollbar ===== */
QScrollBar:vertical {
    background-color: #181825;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background-color: #181825;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background-color: #45475a;
    border-radius: 5px;
    min-width: 30px;
}

/* ===== Progress Bar ===== */
QProgressBar {
    background-color: #313244;
    border: none;
    border-radius: 4px;
    text-align: center;
    color: #cdd6f4;
    height: 8px;
}
QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 4px;
}

/* ===== Tooltip ===== */
QToolTip {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
}

/* ===== Splitter ===== */
QSplitter::handle {
    background-color: #313244;
}
QSplitter::handle:horizontal {
    width: 3px;
}
QSplitter::handle:vertical {
    height: 3px;
}
"""
