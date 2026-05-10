"""
ui/tabs/smart_tools_tab.py
───────────────────────────
Smart tools: backup/restore, battery analyser, performance monitor,
cache cleaner, storage analyser.
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QPlainTextEdit,
    QProgressBar, QFileDialog, QTableWidget,
    QTableWidgetItem, QHeaderView,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer

from diagnostics.diagnostics import DiagnosticsTools
from adb.adb_manager import AdbRunner, AdbThreadManager
from ui.widgets.toast import Toast

log = logging.getLogger(__name__)


class _Worker(QThread):
    result_ready = Signal(bool, str)
    progress     = Signal(int, str)

    def __init__(self, fn, *args):
        super().__init__()
        self.fn   = fn
        self.args = args

    def run(self):
        try:
            r = self.fn(*self.args)
            if isinstance(r, tuple):
                self.result_ready.emit(*r)
            else:
                self.result_ready.emit(True, str(r))
        except Exception as exc:
            self.result_ready.emit(False, str(exc))


class SmartToolsTab(QWidget):

    def __init__(
        self, runner: AdbRunner, adb_mgr: AdbThreadManager, get_serial, parent=None
    ):
        super().__init__(parent)
        self.runner     = runner
        self.adb_mgr    = adb_mgr
        self.diag       = DiagnosticsTools(runner)
        self.get_serial = get_serial
        self._build_ui()
        self._perf_timer: QTimer | None = None

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("الأدوات الذكية  •  Smart Tools")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        # ── Backup / Restore ─────────────────────────────────
        grp_bak = QGroupBox("Backup & Restore")
        gb = QVBoxLayout(grp_bak)
        row_bak = QHBoxLayout()
        self.backup_path_edit = QLabel("No path selected")
        btn_bak_browse = QPushButton("Browse")
        btn_bak_browse.clicked.connect(self._browse_backup_path)
        self.backup_dest = ""
        btn_backup = QPushButton("⬇  ADB Backup")
        btn_backup.setObjectName("primaryBtn")
        btn_backup.clicked.connect(self._backup)
        row_bak.addWidget(self.backup_path_edit, 1)
        row_bak.addWidget(btn_bak_browse)
        row_bak.addWidget(btn_backup)
        gb.addLayout(row_bak)
        self.pb_backup = QProgressBar()
        self.pb_backup.setValue(0)
        gb.addWidget(self.pb_backup)
        root.addWidget(grp_bak)

        # ── Cache Cleaner ────────────────────────────────────
        grp_cache = QGroupBox("Cache Cleaner")
        gc = QHBoxLayout(grp_cache)
        btn_clear_cache = QPushButton("🗑  Clear System Cache")
        btn_clear_cache.setObjectName("warningBtn")
        btn_clear_cache.clicked.connect(self._clear_cache)
        self.lbl_cache_result = QLabel("")
        gc.addWidget(btn_clear_cache)
        gc.addWidget(self.lbl_cache_result, 1)
        root.addWidget(grp_cache)

        # ── Battery Analyser ─────────────────────────────────
        grp_batt = QGroupBox("Battery Analysis")
        gbat = QVBoxLayout(grp_batt)
        btn_batt = QPushButton("🔋  Analyse Battery")
        btn_batt.setObjectName("primaryBtn")
        btn_batt.clicked.connect(self._analyse_battery)
        self.batt_table = QTableWidget(0, 2)
        self.batt_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.batt_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.batt_table.setMaximumHeight(160)
        self.batt_table.setEditTriggers(QTableWidget.NoEditTriggers)
        gbat.addWidget(btn_batt)
        gbat.addWidget(self.batt_table)
        root.addWidget(grp_batt)

        # ── Performance Monitor ───────────────────────────────
        grp_perf = QGroupBox("Performance Monitor  (live)")
        gp = QVBoxLayout(grp_perf)
        perf_row = QHBoxLayout()
        self.btn_start_perf = QPushButton("▶  Start Monitor")
        self.btn_start_perf.setObjectName("successBtn")
        self.btn_start_perf.clicked.connect(self._toggle_perf)
        self.lbl_ram_live  = QLabel("RAM: —")
        self.lbl_cpu_live  = QLabel("CPU: —")
        for lbl in (self.lbl_ram_live, self.lbl_cpu_live):
            lbl.setObjectName("infoValue")
        perf_row.addWidget(self.btn_start_perf)
        perf_row.addWidget(self.lbl_ram_live)
        perf_row.addWidget(self.lbl_cpu_live)
        perf_row.addStretch()
        gp.addLayout(perf_row)
        root.addWidget(grp_perf)

        # ── Storage Analyser ──────────────────────────────────
        grp_stor = QGroupBox("Storage Analyser")
        gs = QVBoxLayout(grp_stor)
        btn_stor = QPushButton("📊  Analyse Storage")
        btn_stor.clicked.connect(self._analyse_storage)
        self.stor_table = QTableWidget(0, 5)
        self.stor_table.setHorizontalHeaderLabels(
            ["Mount", "Total", "Used", "Free", "Use%"]
        )
        self.stor_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.stor_table.setMaximumHeight(140)
        self.stor_table.setEditTriggers(QTableWidget.NoEditTriggers)
        gs.addWidget(btn_stor)
        gs.addWidget(self.stor_table)
        root.addWidget(grp_stor)

        # ── Log ──────────────────────────────────────────────
        self.smart_log = QPlainTextEdit()
        self.smart_log.setObjectName("logViewer")
        self.smart_log.setReadOnly(True)
        self.smart_log.setMaximumHeight(100)
        root.addWidget(self.smart_log)

    # ── Helpers ──────────────────────────────────────────────

    def _serial(self) -> str:
        s = self.get_serial()
        if not s:
            Toast.show_message(self, "No device selected!", "error")
        return s

    def _log(self, msg: str) -> None:
        self.smart_log.appendPlainText(msg)

    def _run(self, fn, *args, on_done=None) -> None:
        worker = _Worker(fn, *args)
        if on_done:
            worker.result_ready.connect(on_done)
        worker.result_ready.connect(
            lambda ok, msg: self._log(msg)
        )
        worker.start()
        self._worker = worker

    # ── Actions ──────────────────────────────────────────────

    def _browse_backup_path(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Backup destination", "backup.ab", "ADB Backup (*.ab)"
        )
        if path:
            self.backup_dest = path
            self.backup_path_edit.setText(path)

    def _backup(self) -> None:
        serial = self._serial()
        if not serial or not self.backup_dest:
            Toast.show_message(self, "Select backup destination", "warning")
            return
        self.pb_backup.setValue(30)
        self._log(f"Starting ADB backup → {self.backup_dest}")
        self._run(
            self.diag.backup_device, serial, self.backup_dest,
            on_done=lambda ok, msg: (
                self.pb_backup.setValue(100),
                Toast.show_message(
                    self, "Backup complete!" if ok else msg,
                    "success" if ok else "error",
                ),
            ),
        )

    def _clear_cache(self) -> None:
        serial = self._serial()
        if not serial:
            return
        ok, msg = self.diag.clear_system_cache(serial)
        self.lbl_cache_result.setText("Cache cleared!" if ok else msg)
        Toast.show_message(self, "Cache cleared" if ok else msg,
                           "success" if ok else "error")

    def _analyse_battery(self) -> None:
        serial = self._serial()
        if not serial:
            return
        data = self.diag.get_battery_full(serial)
        self.batt_table.setRowCount(len(data))
        for row, (k, v) in enumerate(data.items()):
            self.batt_table.setItem(row, 0, QTableWidgetItem(k))
            self.batt_table.setItem(row, 1, QTableWidgetItem(v))

    def _toggle_perf(self) -> None:
        if self._perf_timer and self._perf_timer.isActive():
            self._perf_timer.stop()
            self.btn_start_perf.setText("▶  Start Monitor")
            self.btn_start_perf.setObjectName("successBtn")
        else:
            self._perf_timer = QTimer(self)
            self._perf_timer.timeout.connect(self._update_perf)
            self._perf_timer.start(3000)
            self.btn_start_perf.setText("■  Stop Monitor")
            self.btn_start_perf.setObjectName("dangerBtn")

    def _update_perf(self) -> None:
        serial = self.get_serial()
        if not serial:
            return
        ram = self.diag.get_ram_usage(serial)
        self.lbl_ram_live.setText(
            f"RAM: {ram.get('MemAvailable','?')} free / {ram.get('MemTotal','?')} total"
        )

    def _analyse_storage(self) -> None:
        serial = self._serial()
        if not serial:
            return
        data = self.diag.get_storage_full(serial)
        self.stor_table.setRowCount(len(data))
        for row, (mount, info) in enumerate(data.items()):
            self.stor_table.setItem(row, 0, QTableWidgetItem(mount))
            self.stor_table.setItem(row, 1, QTableWidgetItem(info.get("total", "")))
            self.stor_table.setItem(row, 2, QTableWidgetItem(info.get("used", "")))
            self.stor_table.setItem(row, 3, QTableWidgetItem(info.get("avail", "")))
            self.stor_table.setItem(row, 4, QTableWidgetItem(info.get("use%", "")))
