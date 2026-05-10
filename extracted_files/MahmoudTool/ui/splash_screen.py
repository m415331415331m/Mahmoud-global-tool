"""
ui/splash_screen.py
───────────────────
Animated splash screen shown during startup.
"""

from PySide6.QtWidgets import QSplashScreen, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QLinearGradient, QPen


class SplashScreen(QSplashScreen):
    """Dark-mode splash with animated progress bar."""

    def __init__(self) -> None:
        pixmap = self._build_pixmap()
        super().__init__(pixmap, Qt.WindowStaysOnTopHint)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self._progress = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

    # ── Build the static background pixmap ──────────────────

    @staticmethod
    def _build_pixmap() -> QPixmap:
        W, H = 560, 320
        pm = QPixmap(W, H)
        pm.fill(Qt.transparent)

        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)

        # Background
        p.setBrush(QColor("#0D1117"))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, W, H, 16, 16)

        # Accent line top
        grad = QLinearGradient(0, 0, W, 0)
        grad.setColorAt(0.0, QColor("#1F6FEB"))
        grad.setColorAt(0.5, QColor("#58A6FF"))
        grad.setColorAt(1.0, QColor("#1F6FEB"))
        p.setBrush(grad)
        p.drawRect(0, 0, W, 3)

        # Border
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor("#21262D"), 1))
        p.drawRoundedRect(1, 1, W - 2, H - 2, 15, 15)

        # Title
        p.setPen(QColor("#58A6FF"))
        f = QFont("Segoe UI", 18, QFont.Bold)
        p.setFont(f)
        p.drawText(0, 60, W, 40, Qt.AlignCenter, "Mahmoud AI Global Tool")

        # Subtitle
        p.setPen(QColor("#E2E8F0"))
        f2 = QFont("Segoe UI", 13)
        p.setFont(f2)
        p.drawText(0, 100, W, 30, Qt.AlignCenter, "Ultimate 2026  •  v2.0")

        # Version tag
        p.setPen(QColor("#484F58"))
        f3 = QFont("Segoe UI", 10)
        p.setFont(f3)
        p.drawText(0, 240, W, 20, Qt.AlignCenter, "Professional Android Maintenance Tool")

        p.end()
        return pm

    # ── Animated progress tick ───────────────────────────────

    def _tick(self) -> None:
        self._progress = min(self._progress + 2, 100)
        self.repaint()

    def drawContents(self, painter: QPainter) -> None:
        W = self.width()
        H = self.height()

        # Progress bar track
        BAR_Y  = H - 40
        BAR_H  = 4
        BAR_X  = 40
        BAR_W  = W - 80

        painter.setBrush(QColor("#21262D"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(BAR_X, BAR_Y, BAR_W, BAR_H, 2, 2)

        # Progress bar fill
        fill_w = int(BAR_W * self._progress / 100)
        if fill_w > 0:
            grad = QLinearGradient(BAR_X, 0, BAR_X + BAR_W, 0)
            grad.setColorAt(0.0, QColor("#1F6FEB"))
            grad.setColorAt(1.0, QColor("#58A6FF"))
            painter.setBrush(grad)
            painter.drawRoundedRect(BAR_X, BAR_Y, fill_w, BAR_H, 2, 2)

        # Percentage text
        painter.setPen(QColor("#8B949E"))
        f = QFont("Segoe UI", 10)
        painter.setFont(f)
        painter.drawText(0, BAR_Y + 12, W, 20, Qt.AlignCenter,
                         f"Loading… {self._progress}%")
