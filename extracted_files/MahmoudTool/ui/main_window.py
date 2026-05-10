"""
ui/main_window.py  — v2 (complete, all 15 tabs)
"""
import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget,
    QSizePolicy, QFrame, QStatusBar,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QIcon

from core.config             import AppConfig
from core.database           import DatabaseManager
from core.backup_manager     import BackupManager
from core.tools_downloader   import PlatformToolsManager
from core.logger             import get_logger
from adb.adb_manager         import AdbRunner, AdbThreadManager
from adb.sideload_manager    import SideloadManager
from fastboot.fastboot_manager import FastbootRunner, FastbootThreadManager
from drivers.driver_manager  import DriverManager

from ui.tabs.dashboard_tab    import DashboardTab
from ui.tabs.adb_tab          import AdbTab
from ui.tabs.fastboot_tab     import FastbootTab
from ui.tabs.localization_tab import LocalizationTab
from ui.tabs.network_tab      import NetworkTab
from ui.tabs.volte_tab        import VoLTETab
from ui.tabs.samsung_tab      import SamsungTab
from ui.tabs.xiaomi_tab       import XiaomiTab
from ui.tabs.qualcomm_tab     import QualcommTab, MtkTab
from ui.tabs.smart_tools_tab  import SmartToolsTab
from ui.tabs.backup_tab       import BackupTab
from ui.tabs.assistant_tab    import AssistantTab
from ui.tabs.database_tab     import DatabaseTab
from ui.tabs.settings_tab     import SettingsTab

log = get_logger(__name__)


class NavButton(QPushButton):
    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(f"  {icon}  {label}", parent)
        self.setCheckable(True)
        self.setFixedHeight(40)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)

    def setActive(self, active: bool) -> None:
        self.setChecked(active)
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class Sidebar(QWidget):
    nav_changed = Signal(int)

    _NAV_ITEMS = [
        ("🏠", "Dashboard",        0),
        ("🔧", "ADB Tools",        1),
        ("⚡", "Fastboot",         2),
        ("🌐", "Localization",     3),
        ("📡", "Yemen Networks",   4),
        ("📞", "VoLTE Fix",        5),
        ("📱", "Samsung",          6),
        ("🔴", "Xiaomi",           7),
        ("🔷", "Qualcomm",         8),
        ("🟢", "MediaTek",         9),
        ("🧠", "Smart Tools",      10),
        ("💾", "Backup & Restore", 11),
        ("🤖", "Assistant",        12),
        ("🗄", "Database",          13),
        ("⚙", "Settings",          14),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)
        self._buttons: list[NavButton] = []
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 10)
        layout.setSpacing(1)

        brand = QLabel(
            '<span style="color:#58A6FF;font-size:13px;font-weight:700;">'
            'Mahmoud AI</span><br>'
            '<span style="color:#8B949E;font-size:9px;">Device Service Suite 2026</span>'
        )
        brand.setTextFormat(Qt.RichText)
        brand.setAlignment(Qt.AlignCenter)
        brand.setContentsMargins(0, 6, 0, 12)
        layout.addWidget(brand)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)
        layout.addSpacing(4)

        for icon, label, idx in self._NAV_ITEMS:
            btn = NavButton(icon, label)
            btn.clicked.connect(lambda ch=False, i=idx: self._on_nav(i))
            self._buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()
        ver = QLabel("v2.0.2026  •  Offline Ready")
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet("color:#484F58;font-size:9px;")
        layout.addWidget(ver)
        self._buttons[0].setActive(True)

    def _on_nav(self, idx: int) -> None:
        for i, btn in enumerate(self._buttons):
            btn.setActive(i == idx)
        self.nav_changed.emit(idx)


class MainWindow(QMainWindow):

    def __init__(self, config: AppConfig, db: DatabaseManager,
                 base_dir: Path, parent=None):
        super().__init__(parent)
        self.config   = config
        self.db       = db
        self.base_dir = base_dir

        pt_mgr   = PlatformToolsManager(base_dir / "tools")
        adb_path = config.adb_path if config.adb_path != "adb" else pt_mgr.get_adb_path()
        fb_path  = config.fastboot_path if config.fastboot_path != "fastboot" else pt_mgr.get_fastboot_path()

        self.adb_runner   = AdbRunner(adb_path)
        self.fb_runner    = FastbootRunner(fb_path)
        self.adb_mgr      = AdbThreadManager(self.adb_runner)
        self.fb_mgr       = FastbootThreadManager(self.fb_runner)
        self.backup_mgr   = BackupManager(adb_path, base_dir / "backups")
        self.driver_mgr   = DriverManager(base_dir / "drivers")
        self.sideload_mgr = SideloadManager(adb_path)
        self._current_serial = ""

        self._setup_window()
        self._build_ui()
        self._connect_signals()
        self._start_status_timer()
        log.info("MainWindow ready — ADB: %s", adb_path)

    def _setup_window(self) -> None:
        self.setWindowTitle("Mahmoud AI Device Service Suite 2026")
        self.setMinimumSize(1200, 750)
        self.resize(1440, 860)
        icon = self.base_dir / "assets" / "icon.ico"
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar()
        root.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("contentArea")
        root.addWidget(self.stack, 1)
        self._build_all_tabs()

        sb = QStatusBar()
        self.setStatusBar(sb)
        self.lbl_device  = QLabel("  ⬤  No device")
        self.lbl_adb     = QLabel("  ADB: checking…")
        self.lbl_version = QLabel("  Mahmoud AI 2026  ")
        sb.addWidget(self.lbl_device)
        sb.addWidget(self.lbl_adb)
        sb.addPermanentWidget(self.lbl_version)

    def _build_all_tabs(self) -> None:
        gs = lambda: self._current_serial

        tabs = [
            DashboardTab(self.adb_runner, self.adb_mgr),          # 0
            AdbTab(self.adb_runner, self.adb_mgr, gs),             # 1
            FastbootTab(self.fb_runner, self.fb_mgr, gs),          # 2
            LocalizationTab(self.adb_runner, gs),                  # 3
            NetworkTab(self.adb_runner, gs),                       # 4
            VoLTETab(self.adb_runner, gs),                         # 5
            SamsungTab(self.adb_runner, gs),                       # 6
            XiaomiTab(self.adb_runner, gs),                        # 7
            QualcommTab(self.adb_runner, gs),                      # 8
            MtkTab(self.adb_runner, gs),                           # 9
            SmartToolsTab(self.adb_runner, self.adb_mgr, gs),     # 10
            BackupTab(self.backup_mgr, gs),                        # 11
            AssistantTab(),                                        # 12
            DatabaseTab(self.db),                                  # 13
            SettingsTab(self.config),                              # 14
        ]
        self.tab_dashboard = tabs[0]
        for tab in tabs:
            self.stack.addWidget(tab)

    def _connect_signals(self) -> None:
        self.sidebar.nav_changed.connect(self.stack.setCurrentIndex)
        self.tab_dashboard.device_selected.connect(self._on_device_selected)

    def _on_device_selected(self, serial: str) -> None:
        self._current_serial = serial
        if serial:
            self.lbl_device.setText(f"  ⬤  {serial}")
            self.lbl_device.setStyleSheet("color:#56D364;")
            try:
                self.db.upsert_device(serial)
            except Exception:
                pass
        else:
            self.lbl_device.setText("  ⬤  No device")
            self.lbl_device.setStyleSheet("color:#8B949E;")

    def _start_status_timer(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_status)
        self._timer.start(5000)
        self._update_status()

    def _update_status(self) -> None:
        try:
            n = len(self.adb_runner.get_devices())
            self.lbl_adb.setText(f"  ADB: {n} device{'s' if n!=1 else ''}")
        except Exception:
            self.lbl_adb.setText("  ADB: unavailable")

    def closeEvent(self, event) -> None:
        self.config.save()
        log.info("Application closed")
        event.accept()
