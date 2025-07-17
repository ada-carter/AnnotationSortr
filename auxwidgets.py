"""
Auxiliary widgets for tinySort application.
Contains reusable UI components like clickable labels and custom views.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QLabel, QGraphicsView, QFrame

# ─────────────────────────────────────────────────────────────
# AUX WIDGETS
# ─────────────────────────────────────────────────────────────
class ClickableLabel(QLabel):
    clicked = pyqtSignal(int)
    def __init__(self, idx:int, parent=None):
        super().__init__(parent)
        self.idx = idx
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(
            "border:1px solid rgba(255,255,255,0.2); border-radius: 4px; "
            "background-color: rgba(40,40,40,120); margin: 2px;"
        )
        
    def enterEvent(self, event):
        self.setStyleSheet(
            "border:1px solid rgba(52,152,219,0.8); border-radius: 4px; "
            "background-color: rgba(52,152,219,60); margin: 2px;"
        )
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.setStyleSheet(
            "border:1px solid rgba(255,255,255,0.2); border-radius: 4px; "
            "background-color: rgba(40,40,40,120); margin: 2px;"
        )
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.idx)
        super().mousePressEvent(event)

class ZoomGraphicsView(QGraphicsView):
    """GraphicsView that emits scaleChanged on Ctrl+wheel zoom."""
    scaleChanged = pyqtSignal(float)  # new scale factor from SCALES list approx
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_scale = 1.0
    def wheelEvent(self, e: QWheelEvent):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = e.angleDelta().y()
            factor = 1.1 if delta>0 else 1/1.1
            self._current_scale *= factor
            # clamp for sanity
            self._current_scale = max(min(self._current_scale, 5.0), 0.05)
            self.scaleChanged.emit(self._current_scale)
            e.accept()
        else:
            super().wheelEvent(e)