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

# Ensure running from project root (dynamic, never hardcoded)
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# DPI Awareness Always
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# Safe PySide6 handling
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt, QTranslator, QLocale
    from PySide6.QtGui import QIcon, QFont, QFontDatabase
except ImportError as e:
    sys.stderr.write(f"Missing PySide6: {e}\n")
    sys.exit(1)

# Internal dynamic imports
try:
    from core.config import AppConfig
    from core.logger import setup_logger
    from core.database import DatabaseManager
    from ui.main_window import MainWindow
    from ui.splash_screen import SplashScreen
except ImportError as err:
    sys.stderr.write(f"Import error: {err}\n")
    sys.exit(1)

def load_fonts() -> None:
    """Load all custom fonts from assets - robust to missing files."""
    font_dir = BASE_DIR / "assets" / "fonts"
    if font_dir.exists():
        for ext in ("*.ttf", "*.otf"):
            for font_file in font_dir.glob(ext):
                try:
                    QFontDatabase.addApplicationFont(str(font_file))
                except Exception:
                    continue

def apply_stylesheet(app: QApplication, config) -> None:
    qss_path = BASE_DIR / "assets" / "styles" / "dark_theme.qss"
    if qss_path.exists():
        try:
            app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
        except Exception:
            pass

def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Mahmoud AI Global Tool Ultimate 2026")
    app.setApplicationVersion("2.0.2026")
    app.setOrganizationName("Mahmoud AI")

    config_path = BASE_DIR / "config.json"
    config = AppConfig(config_path if config_path.exists() else None)
    setup_logger(BASE_DIR / "logs")

    db_path = BASE_DIR / "data" / "tool.db"
    db = DatabaseManager(db_path)
    try:
        db.initialize()
    except Exception as e:
        print(f"DB init error: {e}")

    load_fonts()
    apply_stylesheet(app, config)

    splash = SplashScreen()
    splash.show()
    app.processEvents()

    window = MainWindow(config=config, db=db, base_dir=BASE_DIR)
    splash.finish(window)
    window.show()

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
