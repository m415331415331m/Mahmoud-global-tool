"""
ui/tabs/qualcomm_tab.py
────────────────────────
Qualcomm & MediaTek detection and diagnostics.
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from diagnostics.diagnostics import DiagnosticsTools
from adb.adb_manager import AdbRunner
from ui.widgets.toast import Toast

log = logging.getLogger(__name__)


class QualcommTab(QWidget):

    def __init__(self, runner: AdbRunner, get_serial, parent=None):
        super().__init__(parent)
        self.runner     = runner
        self.diag       = DiagnosticsTools(runner)
        self.get_serial = get_serial
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("Qualcomm Tools")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        # ── Detection ────────────────────────────────────────
        grp_det = QGroupBox("Qualcomm Device Detection")
        gd = QVBoxLayout(grp_det)
        btn_detect = QPushButton("⟳  Detect Qualcomm")
        btn_detect.setObjectName("primaryBtn")
        btn_detect.clicked.connect(self._detect)

        self.qcom_table = QTableWidget(0, 2)
        self.qcom_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.qcom_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.qcom_table.setMaximumHeight(130)
        self.qcom_table.setEditTriggers(QTableWidget.NoEditTriggers)
        gd.addWidget(btn_detect)
        gd.addWidget(self.qcom_table)
        root.addWidget(grp_det)

        # ── Diagnostics ──────────────────────────────────────
        grp_diag = QGroupBox("Qualcomm Diagnostics")
        gdg = QHBoxLayout(grp_diag)
        btn_diag = QPushButton("Check DIAG Port")
        btn_diag.clicked.connect(self._check_diag)
        self.lbl_diag = QLabel("—")
        self.lbl_diag.setObjectName("infoValue")
        gdg.addWidget(btn_diag)
        gdg.addWidget(QLabel("Status:"))
        gdg.addWidget(self.lbl_diag)
        gdg.addStretch()
        root.addWidget(grp_diag)

        # ── CPU Info ─────────────────────────────────────────
        grp_cpu = QGroupBox("CPU Information")
        gc = QVBoxLayout(grp_cpu)
        btn_cpu = QPushButton("⟳  Read CPU Info")
        btn_cpu.clicked.connect(self._read_cpu)
        gc.addWidget(btn_cpu)
        self.cpu_table = QTableWidget(0, 2)
        self.cpu_table.setHorizontalHeaderLabels(["Field", "Value"])
        self.cpu_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.cpu_table.setMaximumHeight(140)
        self.cpu_table.setEditTriggers(QTableWidget.NoEditTriggers)
        gc.addWidget(self.cpu_table)
        root.addWidget(grp_cpu)

        # ── Log ──────────────────────────────────────────────
        self.qcom_log = QPlainTextEdit()
        self.qcom_log.setObjectName("logViewer")
        self.qcom_log.setReadOnly(True)
        root.addWidget(self.qcom_log, 1)

    def _serial(self) -> str:
        s = self.get_serial()
        if not s:
            Toast.show_message(self, "No device selected!", "error")
        return s

    def _log(self, msg: str) -> None:
        self.qcom_log.appendPlainText(msg)

    def _fill_table(self, table: QTableWidget, data: dict) -> None:
        table.setRowCount(len(data))
        for row, (k, v) in enumerate(data.items()):
            table.setItem(row, 0, QTableWidgetItem(str(k)))
            item = QTableWidgetItem(str(v))
            if str(v).lower() in ("true", "yes", "1"):
                item.setForeground(QColor("#56D364"))
            elif str(v).lower() in ("false", "no", "0"):
                item.setForeground(QColor("#FF7B72"))
            table.setItem(row, 1, item)

    def _detect(self) -> None:
        serial = self._serial()
        if not serial:
            return
        data = self.diag.detect_qualcomm(serial)
        self._fill_table(self.qcom_table, data)
        is_qcom = data.get("is_qualcomm", False)
        Toast.show_message(
            self,
            f"Qualcomm detected: {data.get('platform','?')}" if is_qcom
            else "Not a Qualcomm device",
            "success" if is_qcom else "warning",
        )

    def _check_diag(self) -> None:
        serial = self._serial()
        if not serial:
            return
        status = self.diag.check_diag_mode(serial)
        self.lbl_diag.setText(status)
        self._log(f"DIAG port: {status}")

    def _read_cpu(self) -> None:
        serial = self._serial()
        if not serial:
            return
        data = self.diag.get_cpu_info(serial)
        self._fill_table(self.cpu_table, {
            k: v for k, v in data.items() if k != "top_snapshot"
        })
        if "top_snapshot" in data:
            self._log(data["top_snapshot"])


class MtkTab(QWidget):
    """MediaTek detection and preloader diagnostics."""

    def __init__(self, runner: AdbRunner, get_serial, parent=None):
        super().__init__(parent)
        self.runner     = runner
        self.diag       = DiagnosticsTools(runner)
        self.get_serial = get_serial
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("MediaTek (MTK) Tools")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        # ── Detection ────────────────────────────────────────
        grp_det = QGroupBox("MTK Device Detection")
        gd = QVBoxLayout(grp_det)
        btn_detect = QPushButton("⟳  Detect MediaTek")
        btn_detect.setObjectName("primaryBtn")
        btn_detect.clicked.connect(self._detect)

        self.mtk_table = QTableWidget(0, 2)
        self.mtk_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.mtk_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.mtk_table.setMaximumHeight(120)
        self.mtk_table.setEditTriggers(QTableWidget.NoEditTriggers)
        gd.addWidget(btn_detect)
        gd.addWidget(self.mtk_table)
        root.addWidget(grp_det)

        # ── Preloader ────────────────────────────────────────
        grp_pre = QGroupBox("Preloader / USB Port Detection")
        gp = QVBoxLayout(grp_pre)
        btn_pre = QPushButton("⟳  Scan Preloader Ports")
        btn_pre.clicked.connect(self._check_preloader)
        self.pre_log = QPlainTextEdit()
        self.pre_log.setObjectName("logViewer")
        self.pre_log.setReadOnly(True)
        self.pre_log.setMaximumHeight(100)
        gp.addWidget(btn_pre)
        gp.addWidget(self.pre_log)
        root.addWidget(grp_pre)

        # ── MTK Log ──────────────────────────────────────────
        self.mtk_log = QPlainTextEdit()
        self.mtk_log.setObjectName("logViewer")
        self.mtk_log.setReadOnly(True)
        root.addWidget(self.mtk_log, 1)

    def _serial(self) -> str:
        s = self.get_serial()
        if not s:
            Toast.show_message(self, "No device selected!", "error")
        return s

    def _log(self, msg: str) -> None:
        self.mtk_log.appendPlainText(msg)

    def _fill_table(self, table: QTableWidget, data: dict) -> None:
        table.setRowCount(len(data))
        for row, (k, v) in enumerate(data.items()):
            table.setItem(row, 0, QTableWidgetItem(str(k)))
            table.setItem(row, 1, QTableWidgetItem(str(v)))

    def _detect(self) -> None:
        serial = self._serial()
        if not serial:
            return
        data = self.diag.detect_mtk(serial)
        self._fill_table(self.mtk_table, data)
        is_mtk = data.get("is_mediatek", False)
        Toast.show_message(
            self,
            f"MediaTek detected: {data.get('platform','?')}" if is_mtk
            else "Not a MediaTek device",
            "success" if is_mtk else "warning",
        )

    def _check_preloader(self) -> None:
        serial = self._serial()
        if not serial:
            return
        result = self.diag.check_preloader(serial)
        self.pre_log.setPlainText(result)
        self._log(f"Preloader ports:\n{result}")
