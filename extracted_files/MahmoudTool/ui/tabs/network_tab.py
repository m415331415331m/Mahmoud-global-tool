"""
ui/tabs/network_tab.py
───────────────────────
Yemen carrier networks tab: APN creation, signal diagnostics, VoLTE check.
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QComboBox,
)
from PySide6.QtCore import Qt, QThread, Signal

from network.yemen_network import YemenNetworkTools, YEMEN_APNS
from adb.adb_manager import AdbRunner
from ui.widgets.toast import Toast

log = logging.getLogger(__name__)


class _NetWorker(QThread):
    result_ready = Signal(bool, str)
    progress     = Signal(int, str)

    def __init__(self, fn, *args):
        super().__init__()
        self.fn   = fn
        self.args = args

    def run(self):
        try:
            r = self.fn(*self.args)
            if isinstance(r, list):
                for name, ok, msg in r:
                    self.progress.emit(0, f"{'✓' if ok else '✗'} {name}: {msg}")
                self.result_ready.emit(True, "Done")
            else:
                ok, msg = r
                self.result_ready.emit(ok, msg)
        except Exception as exc:
            self.result_ready.emit(False, str(exc))


class NetworkTab(QWidget):

    def __init__(self, runner: AdbRunner, get_serial, parent=None):
        super().__init__(parent)
        self.runner   = runner
        self.net_tools = YemenNetworkTools(runner)
        self.get_serial = get_serial
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("شبكات اليمن  •  Yemen Networks")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        # ── SIM Info ─────────────────────────────────────────
        grp_sim = QGroupBox("SIM & Carrier Detection")
        gs = QVBoxLayout(grp_sim)
        btn_read_sim = QPushButton("⟳  Read SIM Info")
        btn_read_sim.setObjectName("primaryBtn")
        btn_read_sim.clicked.connect(self._read_sim)

        self.sim_table = QTableWidget(0, 2)
        self.sim_table.setHorizontalHeaderLabels(["Field", "Value"])
        self.sim_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.sim_table.setMaximumHeight(160)
        self.sim_table.setEditTriggers(QTableWidget.NoEditTriggers)
        gs.addWidget(btn_read_sim)
        gs.addWidget(self.sim_table)
        root.addWidget(grp_sim)

        # ── APN Creator ──────────────────────────────────────
        grp_apn = QGroupBox("Yemen APN Auto-Creator")
        ga = QVBoxLayout(grp_apn)

        # APN table
        self.apn_table = QTableWidget(len(YEMEN_APNS), 4)
        self.apn_table.setHorizontalHeaderLabels(["Carrier", "APN", "MCC", "MNC"])
        self.apn_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.apn_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.apn_table.setMaximumHeight(140)
        for row, apn in enumerate(YEMEN_APNS):
            self.apn_table.setItem(row, 0, QTableWidgetItem(apn.name))
            self.apn_table.setItem(row, 1, QTableWidgetItem(apn.apn))
            self.apn_table.setItem(row, 2, QTableWidgetItem(apn.mcc))
            self.apn_table.setItem(row, 3, QTableWidgetItem(apn.mnc))
        ga.addWidget(self.apn_table)

        btn_row = QHBoxLayout()
        btn_all_apn = QPushButton("⚡  Create ALL Yemen APNs")
        btn_all_apn.setObjectName("successBtn")
        btn_all_apn.clicked.connect(self._create_all_apns)

        btn_sel_apn = QPushButton("Create Selected APN")
        btn_sel_apn.setObjectName("primaryBtn")
        btn_sel_apn.clicked.connect(self._create_selected_apn)
        btn_row.addWidget(btn_all_apn)
        btn_row.addWidget(btn_sel_apn)
        ga.addLayout(btn_row)

        self.pb_apn = QProgressBar()
        self.pb_apn.setValue(0)
        ga.addWidget(self.pb_apn)
        root.addWidget(grp_apn)

        # ── Network Diagnostics ───────────────────────────────
        grp_diag = QGroupBox("Network Diagnostics")
        gd = QVBoxLayout(grp_diag)

        diag_row = QHBoxLayout()
        btn_ping  = QPushButton("🌐  Ping Test (8.8.8.8)")
        btn_ping.clicked.connect(self._ping_test)
        btn_volte = QPushButton("📞  VoLTE / IMS Check")
        btn_volte.clicked.connect(self._check_volte)
        btn_signal = QPushButton("📶  Signal Strength")
        btn_signal.clicked.connect(self._check_signal)
        for b in (btn_ping, btn_volte, btn_signal):
            b.setFixedHeight(38)
            diag_row.addWidget(b)
        gd.addLayout(diag_row)
        root.addWidget(grp_diag)

        # ── Log ──────────────────────────────────────────────
        self.net_log = QPlainTextEdit()
        self.net_log.setObjectName("logViewer")
        self.net_log.setReadOnly(True)
        root.addWidget(self.net_log, 1)

    # ── Helpers ──────────────────────────────────────────────

    def _serial(self) -> str:
        s = self.get_serial()
        if not s:
            Toast.show_message(self, "No device selected!", "error")
        return s

    def _log(self, msg: str) -> None:
        self.net_log.appendPlainText(msg)

    def _run(self, fn, *args, on_done=None) -> None:
        worker = _NetWorker(fn, *args)
        worker.result_ready.connect(
            lambda ok, msg: (
                self._log(msg),
                Toast.show_message(self, msg[:80], "success" if ok else "error"),
                on_done and on_done(ok, msg),
            )
        )
        worker.progress.connect(lambda _, msg: self._log(msg))
        worker.start()
        self._worker = worker

    # ── Actions ──────────────────────────────────────────────

    def _read_sim(self) -> None:
        serial = self._serial()
        if not serial:
            return
        try:
            info = self.net_tools.get_sim_info(serial)
            self.sim_table.setRowCount(len(info))
            for row, (k, v) in enumerate(info.items()):
                self.sim_table.setItem(row, 0, QTableWidgetItem(k))
                self.sim_table.setItem(row, 1, QTableWidgetItem(str(v)))
            Toast.show_message(self, f"Carrier: {info.get('carrier','?')}", "info")
        except Exception as exc:
            Toast.show_message(self, str(exc), "error")

    def _create_all_apns(self) -> None:
        serial = self._serial()
        if not serial:
            return
        self.pb_apn.setValue(0)
        self._log("Creating Yemen APNs…")

        def _with_progress(pct, name):
            self.pb_apn.setValue(pct)
            self._log(f"  ✓ {name}")

        worker = _NetWorker(
            self.net_tools.create_all_yemen_apns, serial, _with_progress
        )
        worker.result_ready.connect(
            lambda ok, msg: (
                self.pb_apn.setValue(100),
                Toast.show_message(self, "All APNs created!" if ok else msg,
                                   "success" if ok else "error"),
            )
        )
        worker.start()
        self._worker = worker

    def _create_selected_apn(self) -> None:
        serial = self._serial()
        if not serial:
            return
        row = self.apn_table.currentRow()
        if row < 0 or row >= len(YEMEN_APNS):
            Toast.show_message(self, "Select an APN from the table", "warning")
            return
        apn = YEMEN_APNS[row]
        ok, msg = self.net_tools.create_apn_via_shell(serial, apn)
        self._log(msg)
        Toast.show_message(self, f"{'Created' if ok else 'Failed'}: {apn.name}",
                           "success" if ok else "error")

    def _ping_test(self) -> None:
        serial = self._serial()
        if not serial:
            return
        self._log("Running ping test…")
        self._run(
            self.net_tools.ping_test, serial,
            on_done=lambda ok, msg: self._log(
                f"Ping result: {'OK' if ok else 'FAILED'}"
            ),
        )

    def _check_volte(self) -> None:
        serial = self._serial()
        if not serial:
            return
        try:
            data = self.net_tools.detect_volte_support(serial)
            for k, v in data.items():
                self._log(f"  {k}: {v}")
            Toast.show_message(
                self,
                f"VoLTE: {'Enabled' if data.get('volte_enabled') else 'Disabled'}",
                "info",
            )
        except Exception as exc:
            Toast.show_message(self, str(exc), "error")

    def _check_signal(self) -> None:
        serial = self._serial()
        if not serial:
            return
        data = self.net_tools.read_signal_strength(serial)
        self._log(f"Signal:\n{data.get('raw', 'No data')}")
