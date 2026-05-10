"""
ui/tabs/database_tab.py
────────────────────────
Device history, operation logs, export.
"""

import csv
import logging
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog,
    QPlainTextEdit,
)
from PySide6.QtCore import Qt

from core.database import DatabaseManager
from ui.widgets.toast import Toast

log = logging.getLogger(__name__)


class DatabaseTab(QWidget):

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("قاعدة البيانات  •  Database")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        tabs = QTabWidget()
        root.addWidget(tabs)

        tabs.addTab(self._build_devices_tab(),    "📱 Devices")
        tabs.addTab(self._build_operations_tab(), "📋 Operations Log")

    # ── Devices Tab ──────────────────────────────────────────

    def _build_devices_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(8)

        hdr = QHBoxLayout()
        lbl = QLabel("Stored Devices")
        lbl.setObjectName("sectionTitle")
        btn_refresh = QPushButton("⟳ Refresh")
        btn_refresh.clicked.connect(self._load_devices)
        btn_export = QPushButton("⬇ Export CSV")
        btn_export.clicked.connect(self._export_devices)
        hdr.addWidget(lbl)
        hdr.addStretch()
        hdr.addWidget(btn_refresh)
        hdr.addWidget(btn_export)
        v.addLayout(hdr)

        self.dev_table = QTableWidget(0, 9)
        self.dev_table.setHorizontalHeaderLabels([
            "Serial", "Model", "Brand", "Android", "One UI",
            "CSC", "Knox", "Root", "Last Seen",
        ])
        self.dev_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.dev_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.dev_table.setAlternatingRowColors(True)
        self.dev_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.dev_table.setSelectionBehavior(QTableWidget.SelectRows)
        v.addWidget(self.dev_table, 1)

        self._load_devices()
        return w

    def _load_devices(self) -> None:
        devices = self.db.get_devices()
        self.dev_table.setRowCount(len(devices))
        for row, dev in enumerate(devices):
            for col, key in enumerate([
                "serial", "model", "brand", "android_ver",
                "one_ui_ver", "csc", "knox_status", "root_status", "last_seen",
            ]):
                val = dev[key] or ""
                self.dev_table.setItem(row, col, QTableWidgetItem(val))

    def _export_devices(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Devices", f"devices_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV (*.csv)"
        )
        if not path:
            return
        devices = self.db.get_devices()
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Serial", "Model", "Brand", "Android", "One UI",
                "CSC", "Knox", "Root", "Last Seen",
            ])
            for dev in devices:
                writer.writerow([
                    dev["serial"], dev["model"], dev["brand"],
                    dev["android_ver"], dev["one_ui_ver"], dev["csc"],
                    dev["knox_status"], dev["root_status"], dev["last_seen"],
                ])
        Toast.show_message(self, f"Exported to {Path(path).name}", "success")

    # ── Operations Tab ───────────────────────────────────────

    def _build_operations_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(8)

        hdr = QHBoxLayout()
        lbl = QLabel("Operation History")
        lbl.setObjectName("sectionTitle")
        btn_refresh = QPushButton("⟳ Refresh")
        btn_refresh.clicked.connect(self._load_ops)
        btn_export = QPushButton("⬇ Export CSV")
        btn_export.clicked.connect(self._export_ops)
        hdr.addWidget(lbl)
        hdr.addStretch()
        hdr.addWidget(btn_refresh)
        hdr.addWidget(btn_export)
        v.addLayout(hdr)

        self.ops_table = QTableWidget(0, 5)
        self.ops_table.setHorizontalHeaderLabels([
            "Time", "Device", "Operation", "Status", "Detail"
        ])
        self.ops_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.ops_table.setAlternatingRowColors(True)
        self.ops_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.ops_table.setSelectionBehavior(QTableWidget.SelectRows)
        v.addWidget(self.ops_table, 1)

        self._load_ops()
        return w

    def _load_ops(self) -> None:
        ops = self.db.get_operations()
        self.ops_table.setRowCount(len(ops))
        for row, op in enumerate(ops):
            self.ops_table.setItem(row, 0, QTableWidgetItem(str(op["created_at"] or "")))
            self.ops_table.setItem(row, 1, QTableWidgetItem(str(op["serial"] or "")))
            self.ops_table.setItem(row, 2, QTableWidgetItem(str(op["operation"] or "")))
            status_item = QTableWidgetItem(str(op["status"] or ""))
            self.ops_table.setItem(row, 3, status_item)
            self.ops_table.setItem(row, 4, QTableWidgetItem(str(op["detail"] or "")))

    def _export_ops(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Operations",
            f"operations_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV (*.csv)"
        )
        if not path:
            return
        ops = self.db.get_operations(limit=10000)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Time", "Device", "Operation", "Status", "Detail"])
            for op in ops:
                writer.writerow([
                    op["created_at"], op["serial"],
                    op["operation"], op["status"], op["detail"],
                ])
        Toast.show_message(self, f"Exported to {Path(path).name}", "success")
