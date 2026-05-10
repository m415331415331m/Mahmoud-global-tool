"""
ui/tabs/volte_tab.py
─────────────────────
VoLTE / IMS repair tab integrated into Yemen Networks.
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor

from network.volte_fix import VoLTEFixer
from adb.adb_manager import AdbRunner
from ui.widgets.toast import Toast

log = logging.getLogger(__name__)


class _VoLTEWorker(QThread):
    result_ready = Signal(bool, str)

    def __init__(self, fn, *args):
        super().__init__()
        self.fn   = fn
        self.args = args

    def run(self):
        try:
            ok, msg = self.fn(*self.args)
            self.result_ready.emit(ok, msg)
        except Exception as exc:
            self.result_ready.emit(False, str(exc))


class VoLTETab(QWidget):

    def __init__(self, runner: AdbRunner, get_serial, parent=None):
        super().__init__(parent)
        self.runner     = runner
        self.fixer      = VoLTEFixer(runner)
        self.get_serial = get_serial
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("إصلاح VoLTE  •  VoLTE / IMS Fix")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        # ── Status ──────────────────────────────────────────
        grp_status = QGroupBox("IMS / VoLTE Status")
        gs = QVBoxLayout(grp_status)
        btn_read = QPushButton("⟳  Read IMS Status")
        btn_read.setObjectName("primaryBtn")
        btn_read.clicked.connect(self._read_status)

        self.status_table = QTableWidget(0, 2)
        self.status_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.status_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        self.status_table.setMaximumHeight(160)
        self.status_table.setEditTriggers(QTableWidget.NoEditTriggers)
        gs.addWidget(btn_read)
        gs.addWidget(self.status_table)
        root.addWidget(grp_status)

        # ── Fix buttons ──────────────────────────────────────
        grp_fix = QGroupBox("VoLTE Fix Actions")
        gf = QVBoxLayout(grp_fix)

        row1 = QHBoxLayout()
        btn_enable = QPushButton("✓  Enable VoLTE (Generic)")
        btn_enable.setObjectName("successBtn")
        btn_enable.clicked.connect(lambda: self._run(self.fixer.enable_volte))

        btn_sam = QPushButton("📱  Samsung VoLTE Fix")
        btn_sam.setObjectName("primaryBtn")
        btn_sam.clicked.connect(
            lambda: self._run(self.fixer.enable_samsung_volte)
        )

        btn_xmi = QPushButton("🔴  Xiaomi VoLTE Fix")
        btn_xmi.setObjectName("primaryBtn")
        btn_xmi.clicked.connect(
            lambda: self._run(self.fixer.enable_xiaomi_volte)
        )
        row1.addWidget(btn_enable)
        row1.addWidget(btn_sam)
        row1.addWidget(btn_xmi)
        gf.addLayout(row1)

        row2 = QHBoxLayout()
        btn_vowifi = QPushButton("📶  Enable VoWiFi")
        btn_vowifi.clicked.connect(
            lambda: self._run(self.fixer.enable_vowifi)
        )

        btn_reset = QPushButton("↩  Reset IMS Config")
        btn_reset.setObjectName("warningBtn")
        btn_reset.clicked.connect(
            lambda: self._run(self.fixer.reset_ims_config)
        )

        btn_restart = QPushButton("🔄  Restart Telephony")
        btn_restart.clicked.connect(
            lambda: self._run(self.fixer.restart_telephony)
        )
        row2.addWidget(btn_vowifi)
        row2.addWidget(btn_reset)
        row2.addWidget(btn_restart)
        gf.addLayout(row2)
        root.addWidget(grp_fix)

        # ── Yemen Carrier VoLTE ──────────────────────────────
        grp_ye = QGroupBox("Yemen Carrier VoLTE Fix")
        gy = QHBoxLayout(grp_ye)
        self.carrier_combo = QComboBox()
        self.carrier_combo.addItems([
            "Yemen Mobile (421-01)",
            "YOU (421-02)",
            "Sabafon (421-03)",
            "Way (421-04)",
        ])
        btn_ye_fix = QPushButton("⚡  Apply Yemen VoLTE Fix")
        btn_ye_fix.setObjectName("successBtn")
        btn_ye_fix.clicked.connect(self._fix_yemen_volte)
        gy.addWidget(QLabel("Carrier:"))
        gy.addWidget(self.carrier_combo, 1)
        gy.addWidget(btn_ye_fix)
        root.addWidget(grp_ye)

        # ── Log ──────────────────────────────────────────────
        self.volte_log = QPlainTextEdit()
        self.volte_log.setObjectName("logViewer")
        self.volte_log.setReadOnly(True)
        root.addWidget(self.volte_log, 1)

    # ── Helpers ──────────────────────────────────────────────

    def _serial(self) -> str:
        s = self.get_serial()
        if not s:
            Toast.show_message(self, "No device selected!", "error")
        return s

    def _log(self, msg: str) -> None:
        self.volte_log.appendPlainText(msg)

    def _run(self, fn) -> None:
        serial = self._serial()
        if not serial:
            return
        worker = _VoLTEWorker(fn, serial)
        worker.result_ready.connect(
            lambda ok, msg: (
                self._log(msg),
                Toast.show_message(
                    self,
                    "Done!" if ok else f"Failed: {msg[:60]}",
                    "success" if ok else "error",
                ),
            )
        )
        worker.start()
        self._worker = worker

    def _read_status(self) -> None:
        serial = self._serial()
        if not serial:
            return
        data = self.fixer.get_ims_status(serial)
        self.status_table.setRowCount(len(data))
        for row, (k, v) in enumerate(data.items()):
            self.status_table.setItem(row, 0, QTableWidgetItem(str(k)))
            val_item = QTableWidgetItem(str(v))
            if str(v).lower() in ("true", "1", "yes"):
                val_item.setForeground(QColor("#56D364"))
            elif str(v).lower() in ("false", "0", "no"):
                val_item.setForeground(QColor("#FF7B72"))
            self.status_table.setItem(row, 1, val_item)

    def _fix_yemen_volte(self) -> None:
        serial = self._serial()
        if not serial:
            return
        idx = self.carrier_combo.currentIndex()
        fn_map = {
            0: self.fixer.fix_volte_yemen_mobile,
            1: self.fixer.fix_volte_you,
            2: self.fixer.enable_volte,   # Sabafon - generic fix
            3: self.fixer.enable_volte,   # Way - generic fix
        }
        fn = fn_map.get(idx, self.fixer.enable_volte)
        self._run(fn)
