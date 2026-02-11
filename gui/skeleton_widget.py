"""
Interactive skeleton point selector.
Draws a simplified human body figure with clickable joints for selecting tracking target skeleton points.
"""
from typing import Optional, Dict, Tuple
from PyQt6.QtWidgets import QWidget, QToolTip
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QPainterPath, QMouseEvent

from config import SkeletonPoint, SKELETON_POINT_CN

# ---- Simplified body coordinates (normalized 0-1) ----
_BODY: Dict[SkeletonPoint, Tuple[float, float]] = {
    SkeletonPoint.NOSE:            (0.50, 0.06),
    SkeletonPoint.LEFT_EYE:        (0.47, 0.04),
    SkeletonPoint.RIGHT_EYE:       (0.53, 0.04),
    SkeletonPoint.LEFT_EAR:        (0.44, 0.06),
    SkeletonPoint.RIGHT_EAR:       (0.56, 0.06),
    SkeletonPoint.LEFT_SHOULDER:   (0.36, 0.20),
    SkeletonPoint.RIGHT_SHOULDER:  (0.64, 0.20),
    SkeletonPoint.LEFT_ELBOW:      (0.26, 0.36),
    SkeletonPoint.RIGHT_ELBOW:     (0.74, 0.36),
    SkeletonPoint.LEFT_WRIST:      (0.20, 0.50),
    SkeletonPoint.RIGHT_WRIST:     (0.80, 0.50),
    SkeletonPoint.LEFT_HIP:        (0.40, 0.52),
    SkeletonPoint.RIGHT_HIP:       (0.60, 0.52),
    SkeletonPoint.LEFT_KNEE:       (0.38, 0.72),
    SkeletonPoint.RIGHT_KNEE:      (0.62, 0.72),
    SkeletonPoint.LEFT_ANKLE:      (0.36, 0.92),
    SkeletonPoint.RIGHT_ANKLE:     (0.64, 0.92),
}

_BONES = [
    (SkeletonPoint.NOSE, SkeletonPoint.LEFT_EYE),
    (SkeletonPoint.NOSE, SkeletonPoint.RIGHT_EYE),
    (SkeletonPoint.LEFT_EYE, SkeletonPoint.LEFT_EAR),
    (SkeletonPoint.RIGHT_EYE, SkeletonPoint.RIGHT_EAR),
    (SkeletonPoint.NOSE, SkeletonPoint.LEFT_SHOULDER),
    (SkeletonPoint.NOSE, SkeletonPoint.RIGHT_SHOULDER),
    (SkeletonPoint.LEFT_SHOULDER, SkeletonPoint.RIGHT_SHOULDER),
    (SkeletonPoint.LEFT_SHOULDER, SkeletonPoint.LEFT_ELBOW),
    (SkeletonPoint.RIGHT_SHOULDER, SkeletonPoint.RIGHT_ELBOW),
    (SkeletonPoint.LEFT_ELBOW, SkeletonPoint.LEFT_WRIST),
    (SkeletonPoint.RIGHT_ELBOW, SkeletonPoint.RIGHT_WRIST),
    (SkeletonPoint.LEFT_SHOULDER, SkeletonPoint.LEFT_HIP),
    (SkeletonPoint.RIGHT_SHOULDER, SkeletonPoint.RIGHT_HIP),
    (SkeletonPoint.LEFT_HIP, SkeletonPoint.RIGHT_HIP),
    (SkeletonPoint.LEFT_HIP, SkeletonPoint.LEFT_KNEE),
    (SkeletonPoint.RIGHT_HIP, SkeletonPoint.RIGHT_KNEE),
    (SkeletonPoint.LEFT_KNEE, SkeletonPoint.LEFT_ANKLE),
    (SkeletonPoint.RIGHT_KNEE, SkeletonPoint.RIGHT_ANKLE),
]


class SkeletonWidget(QWidget):
    """Interactive skeleton point selector widget"""

    point_selected = pyqtSignal(object)  # Emits SkeletonPoint

    _CLR_BONE = QColor("#45475a")
    _CLR_JOINT = QColor("#89b4fa")
    _CLR_SELECTED = QColor("#f38ba8")
    _CLR_HOVER = QColor("#a6e3a1")
    _CLR_LABEL = QColor("#cdd6f4")
    _CLR_HEAD = QColor("#313244")

    JOINT_RADIUS = 9
    HIT_RADIUS = 16  # Click detection radius

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 400)
        self._selected: SkeletonPoint = SkeletonPoint.NOSE
        self._hovered: Optional[SkeletonPoint] = None
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    # ---- public ----

    def selected_point(self) -> SkeletonPoint:
        return self._selected

    def set_selected(self, pt: SkeletonPoint):
        self._selected = pt
        self.update()

    # ---- Coordinate conversion ----

    def _to_pixel(self, nx: float, ny: float) -> QPointF:
        """Normalized coordinates → pixel coordinates"""
        w, h = self.width(), self.height()
        pad = 18
        return QPointF(pad + nx * (w - 2 * pad), pad + ny * (h - 2 * pad))

    def _hit_test(self, pos) -> Optional[SkeletonPoint]:
        """Return the skeleton point at the mouse position"""
        for sp, (nx, ny) in _BODY.items():
            pp = self._to_pixel(nx, ny)
            dx = pos.x() - pp.x()
            dy = pos.y() - pp.y()
            if dx * dx + dy * dy <= self.HIT_RADIUS ** 2:
                return sp
        return None

    # ---- Drawing ----

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Head circle
        head_c = self._to_pixel(*_BODY[SkeletonPoint.NOSE])
        head_r = 22
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(self._CLR_HEAD))
        p.drawEllipse(head_c, head_r, head_r * 1.15)

        # Bone lines
        pen_bone = QPen(self._CLR_BONE, 3)
        p.setPen(pen_bone)
        for a, b in _BONES:
            pa = self._to_pixel(*_BODY[a])
            pb = self._to_pixel(*_BODY[b])
            p.drawLine(pa, pb)

        # Joint points
        for sp, (nx, ny) in _BODY.items():
            pp = self._to_pixel(nx, ny)
            if sp == self._selected:
                color = self._CLR_SELECTED
                r = self.JOINT_RADIUS + 4
            elif sp == self._hovered:
                color = self._CLR_HOVER
                r = self.JOINT_RADIUS + 2
            else:
                color = self._CLR_JOINT
                r = self.JOINT_RADIUS

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(color))
            p.drawEllipse(pp, r, r)

            # Show name for selected point
            if sp == self._selected or sp == self._hovered:
                label = SKELETON_POINT_CN.get(sp, sp.name)
                font = QFont("Microsoft YaHei", 9, QFont.Weight.Bold)
                p.setFont(font)
                p.setPen(QPen(self._CLR_LABEL))
                p.drawText(
                    QRectF(pp.x() - 50, pp.y() + r + 2, 100, 20),
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                    label,
                )

        p.end()

    # ---- Events ----

    def mouseMoveEvent(self, event: QMouseEvent):  # noqa: N802
        hit = self._hit_test(event.position())
        if hit != self._hovered:
            self._hovered = hit
            self.update()
            if hit:
                QToolTip.showText(
                    event.globalPosition().toPoint(),
                    SKELETON_POINT_CN.get(hit, hit.name),
                )

    def mousePressEvent(self, event: QMouseEvent):  # noqa: N802
        hit = self._hit_test(event.position())
        if hit and hit != self._selected:
            self._selected = hit
            self.update()
            self.point_selected.emit(hit)

    def leaveEvent(self, event):  # noqa: N802
        self._hovered = None
        self.update()
