"""
ui/tabs/samsung_tab.py
───────────────────────
Samsung-specific tools: Knox, CSC, debloat, OTA blocker.
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QPlainTextEdit,
    QListWidget, QListWidgetItem, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor

from samsung.samsung_tools import SamsungTools, SAMSUNG_BLOAT_PACKAGES, CSC_CODES
from adb.adb_manager import AdbRunner
from ui.widgets.toast import Toast

log = logging.getLogger(__name__)


class _SamsungWorker(QThread):
    progress     = Signal(int, str)
    result_ready = Signal(bool, str)

    def __init__(self, fn, *args):
        super().__init__()
        self.fn   = fn
        self.args = args

    def run(self):
        try:
            r = self.fn(*self.args)
            if isinstance(r, list):
                for pkg, ok, msg in r:
                    self.progress.emit(0, f"{'✓' if ok else '✗'} {pkg}")
                self.result_ready.emit(True, f"Done: {len(r)} packages")
            else:
                self.result_ready.emit(*r)
        except Exception as exc:
            self.result_ready.emit(False, str(exc))


class SamsungTab(QWidget):

    def __init__(self, runner: AdbRunner, get_serial, parent=None):
        super().__init__(parent)
        self.runner      = runner
        self.sam_tools   = SamsungTools(runner)
        self.get_serial  = get_serial
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("Samsung Tools")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        # ── Knox & CSC Info ──────────────────────────────────
        grp_info = QGroupBox("Knox & CSC Information")
        gi = QVBoxLayout(grp_info)
        btn_row = QHBoxLayout()
        btn_knox = QPushButton("⟳  Read Knox Status")
        btn_knox.setObjectName("primaryBtn")
        btn_knox.clicked.connect(self._read_knox)
        btn_csc = QPushButton("⟳  Read CSC")
        btn_csc.clicked.connect(self._read_csc)
        btn_oneui = QPushButton("⟳  One UI Version")
        btn_oneui.clicked.connect(self._read_oneui)
        for b in (btn_knox, btn_csc, btn_oneui):
            btn_row.addWidget(b)
        gi.addLayout(btn_row)

        self.info_table = QTableWidget(0, 2)
        self.info_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.info_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.info_table.setMaximumHeight(160)
        self.info_table.setEditTriggers(QTableWidget.NoEditTriggers)
        gi.addWidget(self.info_table)
        root.addWidget(grp_info)

        # ── Debloat ──────────────────────────────────────────
        grp_debloat = QGroupBox(f"Samsung Debloat  ({len(SAMSUNG_BLOAT_PACKAGES)} packages)")
        gd = QVBoxLayout(grp_debloat)

        self.bloat_list = QListWidget()
        self.bloat_list.setMaximumHeight(150)
        for pkg in SAMSUNG_BLOAT_PACKAGES:
            item = QListWidgetItem(pkg)
            item.setCheckState(Qt.Checked)
            self.bloat_list.addItem(item)
        gd.addWidget(self.bloat_list)

        self.pb_debloat = QProgressBar()
        self.pb_debloat.setValue(0)
        gd.addWidget(self.pb_debloat)

        btn_debloat_row = QHBoxLayout()
        btn_debloat_all = QPushButton("⚡  Debloat All Checked")
        btn_debloat_all.setObjectName("dangerBtn")
        btn_debloat_all.clicked.connect(self._debloat_all)
        btn_enable_all = QPushButton("↩  Re-enable All")
        btn_enable_all.setObjectName("successBtn")
        btn_enable_all.clicked.connect(self._enable_all)
        btn_debloat_row.addWidget(btn_debloat_all)
        btn_debloat_row.addWidget(btn_enable_all)
        gd.addLayout(btn_debloat_row)
        root.addWidget(grp_debloat)

        # ── OTA Blocker ──────────────────────────────────────
        grp_ota = QGroupBox("OTA Update Control")
        go = QHBoxLayout(grp_ota)
        btn_block_ota = QPushButton("🛑  Block OTA Updates")
        btn_block_ota.setObjectName("dangerBtn")
        btn_block_ota.clicked.connect(self._block_ota)
        btn_allow_ota = QPushButton("✓  Allow OTA Updates")
        btn_allow_ota.setObjectName("successBtn")
        btn_allow_ota.clicked.connect(self._allow_ota)
        go.addWidget(btn_block_ota)
        go.addWidget(btn_allow_ota)
        root.addWidget(grp_ota)

        # ── Log ──────────────────────────────────────────────
        self.sam_log = QPlainTextEdit()
        self.sam_log.setObjectName("logViewer")
        self.sam_log.setReadOnly(True)
        root.addWidget(self.sam_log, 1)

    # ── Helpers ──────────────────────────────────────────────

    def _serial(self) -> str:
        s = self.get_serial()
        if not s:
            Toast.show_message(self, "No device selected!", "error")
        return s

    def _log(self, msg: str) -> None:
        self.sam_log.appendPlainText(msg)

    def _set_table(self, data: dict) -> None:
        self.info_table.setRowCount(len(data))
        for row, (k, v) in enumerate(data.items()):
            self.info_table.setItem(row, 0, QTableWidgetItem(k))
            item = QTableWidgetItem(str(v))
            if v in ("0", "false", "", "Unknown"):
                item.setForeground(QColor("#8B949E"))
            elif v in ("1", "true"):
                item.setForeground(QColor("#56D364"))
            self.info_table.setItem(row, 1, item)

    # ── Actions ──────────────────────────────────────────────

    def _read_knox(self) -> None:
        serial = self._serial()
        if not serial:
            return
        data = self.sam_tools.get_knox_status(serial)
        self._set_table(data)
        self._log(f"Knox status read: {data}")

    def _read_csc(self) -> None:
        serial = self._serial()
        if not serial:
            return
        csc  = self.sam_tools.get_csc(serial)
        desc = self.sam_tools.get_csc_description(csc)
        self._set_table({"CSC Code": csc, "Region": desc})
        Toast.show_message(self, f"CSC: {csc}  ({desc})", "info")

    def _read_oneui(self) -> None:
        serial = self._serial()
        if not serial:
            return
        ver = self.sam_tools.get_one_ui_version(serial)
        self._set_table({"One UI Version": ver or "Not Samsung / Unknown"})

    def _debloat_all(self) -> None:
        serial = self._serial()
        if not serial:
            return
        # Collect checked packages
        packages = []
        for i in range(self.bloat_list.count()):
            item = self.bloat_list.item(i)
            if item.checkState() == Qt.Checked:
                packages.append(item.text())

        if not packages:
            Toast.show_message(self, "No packages selected", "warning")
            return

        self.pb_debloat.setValue(0)
        self._log(f"Starting debloat: {len(packages)} packages…")

        def _debloat_fn(serial, packages):
            results = []
            for i, pkg in enumerate(packages):
                ok, msg = self.sam_tools.disable_package(serial, pkg)
                results.append((pkg, ok, msg))
            return results

        worker = _SamsungWorker(_debloat_fn, serial, packages)
        worker.progress.connect(lambda pct, msg: (
            self.pb_debloat.setValue(
                int((self.bloat_list.count() - packages.__len__()) / max(len(packages), 1) * 100)
            ),
            self._log(msg),
        ))
        worker.result_ready.connect(lambda ok, msg: (
            self.pb_debloat.setValue(100),
            self._log(msg),
            Toast.show_message(self, msg, "success" if ok else "error"),
        ))
        worker.start()
        self._worker = worker

    def _enable_all(self) -> None:
        serial = self._serial()
        if not serial:
            return
        self._log("Re-enabling all Samsung packages…")
        for pkg in SAMSUNG_BLOAT_PACKAGES:
            ok, msg = self.sam_tools.enable_package(serial, pkg)
            self._log(f"  {pkg}: {msg.strip()}")
        Toast.show_message(self, "All packages re-enabled", "success")

    def _block_ota(self) -> None:
        serial = self._serial()
        if not serial:
            return
        ok, msg = self.sam_tools.block_ota(serial)
        self._log(msg)
        Toast.show_message(self, "OTA blocked" if ok else msg,
                           "warning" if ok else "error")

    def _allow_ota(self) -> None:
        serial = self._serial()
        if not serial:
            return
        ok, msg = self.sam_tools.allow_ota(serial)
        self._log(msg)
        Toast.show_message(self, "OTA allowed" if ok else msg,
                           "success" if ok else "error")
