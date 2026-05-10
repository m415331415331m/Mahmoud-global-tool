"""
ui/widgets/toast.py
────────────────────
Non-blocking toast notification that fades out automatically.
"""

from PySide6.QtWidgets import QLabel, QWidget, QHBoxLayout
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QColor


class Toast(QWidget):
    """
    Floating toast notification.

    Usage:
        Toast.show_message(parent, "File installed!", kind="success")
    """

    KIND_COLORS = {
        "success": ("#238636", "#56D364"),
        "error":   ("#DA3633", "#FF7B72"),
        "warning": ("#BB8009", "#E3B341"),
        "info":    ("#1F6FEB", "#58A6FF"),
    }

    def __init__(self, message: str, kind: str = "info", parent: QWidget = None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        bg_color, text_color = self.KIND_COLORS.get(kind, self.KIND_COLORS["info"])

        icon = {"success": "✓", "error": "✕", "warning": "⚠", "info": "ℹ"}.get(kind, "ℹ")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(10)

        self.label = QLabel(f"{icon}  {message}")
        self.label.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 600;
                border: 1px solid {text_color}40;
            }}
        """)
        layout.addWidget(self.label)
        self.adjustSize()

        # Auto-close after 3 s
        QTimer.singleShot(3000, self.close)

    @classmethod
    def show_message(
        cls,
        parent: QWidget,
        message: str,
        kind: str = "info",
        duration_ms: int = 3000,
    ) -> "Toast":
        toast = cls(message, kind, parent)

        if parent:
            # Position at bottom-right of parent
            pw, ph = parent.width(), parent.height()
            tw, th = toast.sizeHint().width(), toast.sizeHint().height()
            x = parent.mapToGlobal(parent.rect().bottomRight()).x() - tw - 20
            y = parent.mapToGlobal(parent.rect().bottomRight()).y() - th - 20
            toast.move(x, y)
        else:
            toast.move(100, 100)

        toast.show()
        QTimer.singleShot(duration_ms, toast.close)
        return toast
