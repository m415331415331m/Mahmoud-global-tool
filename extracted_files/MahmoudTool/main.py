"""
============================================================
Mahmoud AI Global Tool Ultimate 2026
Main Entry Point
============================================================
Author  : Mahmoud AI
Version : 2.0.2026
License : Professional License
Platform: Windows 10/11 x64
============================================================
"""

import sys
import os
import ctypes
import logging
from pathlib import Path

# ── Make sure we run from the project root ──────────────────
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# ── Enable DPI Awareness on Windows ────────────────────────
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()

# ── PySide6 Imports ─────────────────────────────────────────
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTranslator, QLocale
from PySide6.QtGui import QIcon, QFont, QFontDatabase

# ── Internal Imports ────────────────────────────────────────
from core.config import AppConfig
from core.logger import setup_logger
from core.database import DatabaseManager
from ui.main_window import MainWindow
from ui.splash_screen import SplashScreen


def load_fonts() -> None:
    """Load custom Arabic / Latin fonts from assets."""
    font_dir = BASE_DIR / "assets" / "fonts"
    if font_dir.exists():
        for font_file in font_dir.glob("*.ttf"):
            QFontDatabase.addApplicationFont(str(font_file))
        for font_file in font_dir.glob("*.otf"):
            QFontDatabase.addApplicationFont(str(font_file))


def apply_stylesheet(app: QApplication, config: AppConfig) -> None:
    """Apply the global dark-mode stylesheet."""
    qss_path = BASE_DIR / "assets" / "styles" / "dark_theme.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))


def main() -> int:
    # ── High-DPI scaling ─────────────────────────────────────
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Mahmoud AI Global Tool Ultimate 2026")
    app.setApplicationVersion("2.0.2026")
    app.setOrganizationName("Mahmoud AI")

    # ── Load configuration ───────────────────────────────────
    config = AppConfig(BASE_DIR / "config.json")

    # ── Setup logger ─────────────────────────────────────────
    setup_logger(BASE_DIR / "logs")

    # ── Initialize database ──────────────────────────────────
    db = DatabaseManager(BASE_DIR / "data" / "tool.db")
    db.initialize()

    # ── Fonts & stylesheet ───────────────────────────────────
    load_fonts()
    apply_stylesheet(app, config)

    # ── Splash screen ────────────────────────────────────────
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    # ── Main window ──────────────────────────────────────────
    window = MainWindow(config=config, db=db, base_dir=BASE_DIR)

    splash.finish(window)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
