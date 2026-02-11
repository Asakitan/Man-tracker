"""
Video preview widget
"""
import cv2
import numpy as np
from PyQt6.QtWidgets import QLabel, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from utils.obfuscation import _s


class VideoWidget(QLabel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(320, 240)
        self.setStyleSheet(
            "background-color: #11111b; border: 1px solid #313244; border-radius: 8px;"
        )
        self._show_placeholder()

    def _show_placeholder(self):
        self.setText(
            '<p style="color:#585b70; font-size:16px; text-align:center;">'
            f'{_s("vid_preview")}<br>'
            f'<span style="font-size:12px;">{_s("vid_hint")}</span></p>'
        )

    def update_frame(self, frame: np.ndarray):
        if frame is None or frame.size == 0:
            return

        h, w, ch = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        bytes_per_line = ch * w
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

        # aspect-fit scale
        pixmap = QPixmap.fromImage(qimg).scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(pixmap)

    def clear_view(self):
        self.clear()
        self._show_placeholder()
