"""
ui/tabs/xiaomi_tab.py
──────────────────────
Xiaomi / MIUI / HyperOS tools tab.
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QPlainTextEdit,
    QListWidget, QListWidgetItem, QProgressBar,
    QComboBox,
)
from PySide6.QtCore import Qt, QThread, Signal

from xiaomi.xiaomi_tools import XiaomiTools, MIUI_BLOAT_PACKAGES, XIAOMI_REGIONS
from adb.adb_manager import AdbRunner
from ui.widgets.toast import Toast

log = logging.getLogger(__name__)


class _XiaomiWorker(QThread):
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


class XiaomiTab(QWidget):

    def __init__(self, runner: AdbRunner, get_serial, parent=None):
        super().__init__(parent)
        self.runner     = runner
        self.xmi_tools  = XiaomiTools(runner)
        self.get_serial = get_serial
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("Xiaomi / MIUI / HyperOS Tools")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        # ── Device info ──────────────────────────────────────
        grp_info = QGroupBox("MIUI / HyperOS Information")
        gi = QHBoxLayout(grp_info)
        btn_read = QPushButton("⟳  Read Device Info")
        btn_read.setObjectName("primaryBtn")
        btn_read.clicked.connect(self._read_info)
        self.lbl_miui_ver    = QLabel("—")
        self.lbl_hyperos_ver = QLabel("—")
        self.lbl_region      = QLabel("—")
        for lbl in (self.lbl_miui_ver, self.lbl_hyperos_ver, self.lbl_region):
            lbl.setObjectName("infoValue")
        gi.addWidget(btn_read)
        gi.addWidget(QLabel("MIUI:"))
        gi.addWidget(self.lbl_miui_ver)
        gi.addWidget(QLabel("HyperOS:"))
        gi.addWidget(self.lbl_hyperos_ver)
        gi.addWidget(QLabel("Region:"))
        gi.addWidget(self.lbl_region)
        gi.addStretch()
        root.addWidget(grp_info)

        # ── Region Changer ───────────────────────────────────
        grp_region = QGroupBox("Region Changer")
        gr = QHBoxLayout(grp_region)
        gr.addWidget(QLabel("Target Region:"))
        self.region_combo = QComboBox()
        for code, name in XIAOMI_REGIONS.items():
            self.region_combo.addItem(f"{name}  [{code}]", code)
        btn_change_region = QPushButton("Apply Region")
        btn_change_region.setObjectName("primaryBtn")
        btn_change_region.clicked.connect(self._change_region)
        gr.addWidget(self.region_combo, 1)
        gr.addWidget(btn_change_region)
        root.addWidget(grp_region)

        # ── Debloat ──────────────────────────────────────────
        grp_debloat = QGroupBox(f"MIUI / HyperOS Debloat  ({len(MIUI_BLOAT_PACKAGES)} packages)")
        gd = QVBoxLayout(grp_debloat)

        self.xmi_bloat_list = QListWidget()
        self.xmi_bloat_list.setMaximumHeight(140)
        for pkg in MIUI_BLOAT_PACKAGES:
            item = QListWidgetItem(pkg)
            item.setCheckState(Qt.Checked)
            self.xmi_bloat_list.addItem(item)
        gd.addWidget(self.xmi_bloat_list)

        self.pb_xmi_debloat = QProgressBar()
        self.pb_xmi_debloat.setValue(0)
        gd.addWidget(self.pb_xmi_debloat)

        btn_row = QHBoxLayout()
        btn_debloat = QPushButton("⚡  Debloat MIUI / HyperOS")
        btn_debloat.setObjectName("dangerBtn")
        btn_debloat.clicked.connect(self._debloat)
        btn_row.addWidget(btn_debloat)
        gd.addLayout(btn_row)
        root.addWidget(grp_debloat)

        # ── Recovery ─────────────────────────────────────────
        grp_rec = QGroupBox("Recovery Tools")
        hrec = QHBoxLayout(grp_rec)
        btn_rec = QPushButton("Boot to Recovery (ADB-enabled)")
        btn_rec.clicked.connect(self._boot_recovery)
        hrec.addWidget(btn_rec)
        root.addWidget(grp_rec)

        # ── Log ──────────────────────────────────────────────
        self.xmi_log = QPlainTextEdit()
        self.xmi_log.setObjectName("logViewer")
        self.xmi_log.setReadOnly(True)
        root.addWidget(self.xmi_log, 1)

    # ── Helpers ──────────────────────────────────────────────

    def _serial(self) -> str:
        s = self.get_serial()
        if not s:
            Toast.show_message(self, "No device selected!", "error")
        return s

    def _log(self, msg: str) -> None:
        self.xmi_log.appendPlainText(msg)

    # ── Actions ──────────────────────────────────────────────

    def _read_info(self) -> None:
        serial = self._serial()
        if not serial:
            return
        self.lbl_miui_ver.setText(self.xmi_tools.get_miui_version(serial) or "—")
        self.lbl_hyperos_ver.setText(self.xmi_tools.get_hyperos_version(serial) or "—")
        self.lbl_region.setText(self.xmi_tools.get_region(serial) or "—")

    def _change_region(self) -> None:
        serial = self._serial()
        if not serial:
            return
        region = self.region_combo.currentData()
        ok, msg = self.xmi_tools.change_region(serial, region)
        self._log(msg)
        Toast.show_message(self, f"Region changed to {region}" if ok else msg,
                           "success" if ok else "error")

    def _debloat(self) -> None:
        serial = self._serial()
        if not serial:
            return
        self.pb_xmi_debloat.setValue(0)
        self._log("Starting MIUI debloat…")

        def _progress(pct, name):
            self.pb_xmi_debloat.setValue(pct)
            self._log(f"  ✓ {name}")

        worker = _XiaomiWorker(self.xmi_tools.debloat_miui, serial, _progress)
        worker.result_ready.connect(lambda ok, msg: (
            self.pb_xmi_debloat.setValue(100),
            self._log(msg),
            Toast.show_message(self, msg, "success" if ok else "error"),
        ))
        worker.start()
        self._worker = worker

    def _boot_recovery(self) -> None:
        serial = self._serial()
        if not serial:
            return
        ok, msg = self.xmi_tools.enable_adb_in_recovery(serial)
        self._log(msg)
        Toast.show_message(self, "Booting to recovery…" if ok else msg,
                           "info" if ok else "error")
