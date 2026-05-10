"""
ui/tabs/dashboard_tab.py
─────────────────────────
Main dashboard: connected devices list + device info card + live logs.
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSplitter, QListWidget, QListWidgetItem,
    QPlainTextEdit, QPushButton, QFrame,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor

from ui.widgets.device_card import DeviceCard
from adb.adb_manager import AdbRunner, AdbThreadManager

log = logging.getLogger(__name__)


class DashboardTab(QWidget):
    """Dashboard tab – shows devices, info card, and live logcat."""

    device_selected = Signal(str)   # emits serial

    def __init__(self, runner: AdbRunner, adb_mgr: AdbThreadManager, parent=None):
        super().__init__(parent)
        self.runner  = runner
        self.adb_mgr = adb_mgr
        self._current_serial: str = ""
        self._build_ui()
        self._start_device_poll()

    # ── UI Construction ──────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # ── Page title ───────────────────────────────────────
        title_row = QHBoxLayout()
        lbl = QLabel("Dashboard")
        lbl.setObjectName("pageTitle")
        self.lbl_connected = QLabel("No devices")
        self.lbl_connected.setObjectName("infoKey")
        self.lbl_connected.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        title_row.addWidget(lbl)
        title_row.addStretch()
        title_row.addWidget(self.lbl_connected)
        root.addLayout(title_row)

        # ── Main splitter (left/right) ────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(2)

        # ── Left: device list + card ─────────────────────────
        left = QWidget()
        left_v = QVBoxLayout(left)
        left_v.setContentsMargins(0, 0, 0, 0)
        left_v.setSpacing(12)

        lbl_dev = QLabel("Connected Devices")
        lbl_dev.setObjectName("sectionTitle")
        left_v.addWidget(lbl_dev)

        self.device_list = QListWidget()
        self.device_list.setMaximumHeight(120)
        self.device_list.itemClicked.connect(self._on_device_clicked)
        left_v.addWidget(self.device_list)

        self.device_card = DeviceCard()
        self.device_card.refresh_requested.connect(self._refresh_device_info)
        left_v.addWidget(self.device_card)
        left_v.addStretch()

        splitter.addWidget(left)

        # ── Right: logs ──────────────────────────────────────
        right = QWidget()
        right_v = QVBoxLayout(right)
        right_v.setContentsMargins(0, 0, 0, 0)
        right_v.setSpacing(8)

        log_header = QHBoxLayout()
        lbl_log = QLabel("Live Device Log")
        lbl_log.setObjectName("sectionTitle")
        self.btn_clear_log = QPushButton("Clear")
        self.btn_clear_log.clicked.connect(self._clear_log)
        self.btn_auto_scroll = QPushButton("Auto-scroll: ON")
        self.btn_auto_scroll.setCheckable(True)
        self.btn_auto_scroll.setChecked(True)
        log_header.addWidget(lbl_log)
        log_header.addStretch()
        log_header.addWidget(self.btn_auto_scroll)
        log_header.addWidget(self.btn_clear_log)
        right_v.addLayout(log_header)

        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("logViewer")
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Waiting for device connection…")
        right_v.addWidget(self.log_view)

        splitter.addWidget(right)
        splitter.setSizes([420, 600])
        root.addWidget(splitter, 1)

    # ── Device Polling ───────────────────────────────────────

    def _start_device_poll(self) -> None:
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_devices)
        self._poll_timer.start(2000)

    def _poll_devices(self) -> None:
        try:
            devices = self.runner.get_devices()
        except Exception:
            devices = []

        self.device_list.clear()
        for dev in devices:
            item = QListWidgetItem(
                f"  {dev['serial']}  [{dev['state']}]"
            )
            item.setData(Qt.UserRole, dev["serial"])
            if dev["state"] == "device":
                item.setForeground(QColor("#56D364"))
            elif dev["state"] == "unauthorized":
                item.setForeground(QColor("#E3B341"))
            else:
                item.setForeground(QColor("#FF7B72"))
            self.device_list.addItem(item)

        count = len(devices)
        self.lbl_connected.setText(
            f"{'🟢' if count else '🔴'}  {count} device{'s' if count != 1 else ''} connected"
        )

        # Auto-select first device
        if count and not self._current_serial:
            self.device_list.setCurrentRow(0)
            self._on_device_clicked(self.device_list.item(0))

    # ── Device selection ─────────────────────────────────────

    def _on_device_clicked(self, item: QListWidgetItem) -> None:
        serial = item.data(Qt.UserRole)
        if serial and serial != self._current_serial:
            self._current_serial = serial
            self.device_selected.emit(serial)
            self._refresh_device_info()
            self._start_log_refresh()

    def _refresh_device_info(self) -> None:
        if not self._current_serial:
            return
        self.adb_mgr.start(
            self._current_serial,
            "get_info",
            on_info=self._on_device_info,
        )

    def _on_device_info(self, info) -> None:
        self.device_card.update_from_device_info(info)

    # ── Log refresh ──────────────────────────────────────────

    def _start_log_refresh(self) -> None:
        if not hasattr(self, "_log_timer"):
            self._log_timer = QTimer(self)
            self._log_timer.timeout.connect(self._fetch_log)
        self._log_timer.start(4000)

    def _fetch_log(self) -> None:
        if not self._current_serial:
            return
        try:
            lines = self.runner.get_logcat_lines(self._current_serial, 80)
            for line in lines.splitlines()[-40:]:
                self._append_log(line)
        except Exception:
            pass

    def _append_log(self, line: str) -> None:
        self.log_view.appendPlainText(line)
        if self.btn_auto_scroll.isChecked():
            sb = self.log_view.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _clear_log(self) -> None:
        self.log_view.clear()

    # ── Public ───────────────────────────────────────────────

    @property
    def current_serial(self) -> str:
        return self._current_serial
