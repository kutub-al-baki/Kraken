"""
Modern Compass Widget for ROV Control System
Displays a circular compass with heading indicator
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, pyqtProperty
from PyQt6.QtGui import (
    QPainter,
    QPen,
    QBrush,
    QColor,
    QFont,
    QPainterPath,
    QConicalGradient,
)


class ModernCompass(QWidget):
    """Modern circular compass widget with heading display"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._heading = 0.0
        self.setMinimumSize(180, 180)

    @pyqtProperty(float)
    def heading(self):
        """Get current heading in degrees"""
        return self._heading

    @heading.setter
    def heading(self, value):
        """Set heading in degrees (0-360)"""
        self._heading = value % 360
        self.update()

    def paintEvent(self, event):
        """Draw the compass"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate center and radius
        width = self.width()
        height = self.height()
        size = min(width, height)
        center = QPoint(width // 2, height // 2)
        centerF = QPointF(width / 2, height / 2)
        radius = (size // 2) - 10

        # Draw background circle with gradient
        gradient = QConicalGradient(centerF, 0)
        gradient.setColorAt(0.0, QColor(15, 15, 15))
        gradient.setColorAt(0.5, QColor(10, 10, 10))
        gradient.setColorAt(1.0, QColor(15, 15, 15))

        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(26, 26, 26), 2))
        painter.drawEllipse(center, radius, radius)

        # Draw outer ring with cyan accent
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(0, 212, 255, 100), 3))
        painter.drawEllipse(center, radius - 5, radius - 5)

        # Draw compass markings
        painter.save()
        painter.translate(center)

        # Draw degree markings
        for angle in range(0, 360, 10):
            painter.save()
            painter.rotate(angle)

            if angle % 30 == 0:
                # Major tick marks (every 30 degrees)
                painter.setPen(QPen(QColor(0, 212, 255), 2))
                painter.drawLine(0, -(radius - 15), 0, -(radius - 30))
            else:
                # Minor tick marks
                painter.setPen(QPen(QColor(128, 128, 128), 1))
                painter.drawLine(0, -(radius - 15), 0, -(radius - 25))

            painter.restore()

        painter.restore()

        # Draw cardinal directions (N, E, S, W) - WITHOUT rotation
        font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(0, 212, 255)))

        # North (top)
        painter.drawText(
            QRect(center.x() - 15, center.y() - radius + 35, 30, 20),
            Qt.AlignmentFlag.AlignCenter,
            "N",
        )

        # East (right)
        painter.drawText(
            QRect(center.x() + radius - 45, center.y() - 10, 30, 20),
            Qt.AlignmentFlag.AlignCenter,
            "E",
        )

        # South (bottom)
        painter.drawText(
            QRect(center.x() - 15, center.y() + radius - 55, 30, 20),
            Qt.AlignmentFlag.AlignCenter,
            "S",
        )

        # West (left)
        painter.drawText(
            QRect(center.x() - radius + 15, center.y() - 10, 30, 20),
            Qt.AlignmentFlag.AlignCenter,
            "W",
        )

        painter.save()
        painter.translate(center)

        # Draw heading arrow (pointing to current heading)
        painter.save()
        painter.rotate(-self._heading)  # Rotate to heading

        # Create arrow path
        arrow = QPainterPath()
        arrow.moveTo(0, -(radius - 60))  # Tip
        arrow.lineTo(-8, -(radius - 75))  # Left base
        arrow.lineTo(0, -(radius - 70))  # Center base
        arrow.lineTo(8, -(radius - 75))  # Right base
        arrow.closeSubpath()

        painter.setBrush(QBrush(QColor(234, 138, 53)))
        painter.setPen(QPen(QColor(234, 138, 53, 200), 2))
        painter.drawPath(arrow)

        painter.restore()

        # Draw center circle
        painter.setBrush(QBrush(QColor(234, 138, 53)))
        painter.setPen(QPen(QColor(234, 138, 53, 200), 2))
        painter.drawEllipse(center, 8, 8)

        # Draw heading value in center
        font = QFont("Consolas", 16, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(234, 138, 53)))
        heading_text = f"{int(self._heading)}°"
        text_rect = QRect(center.x() - 40, center.y() + 15, 80, 30)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, heading_text)

        painter.restore()

    def setHeading(self, degrees):
        """Set the compass heading (convenience method)"""
        self.heading = degrees

    def getHeading(self):
        """Get the current heading (convenience method)"""
        return self._heading
