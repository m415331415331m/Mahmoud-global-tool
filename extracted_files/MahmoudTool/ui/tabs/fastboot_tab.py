"""
ui/tabs/fastboot_tab.py
────────────────────────
Fastboot operations tab.
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFileDialog, QComboBox,
    QGroupBox, QPlainTextEdit, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView,
)
from PySide6.QtCore import Qt

from fastboot.fastboot_manager import FastbootRunner, FastbootThreadManager
from ui.widgets.toast import Toast

log = logging.getLogger(__name__)


class FastbootTab(QWidget):

    def __init__(
        self,
        runner: FastbootRunner,
        fb_mgr: FastbootThreadManager,
        get_serial,
        parent=None,
    ):
        super().__init__(parent)
        self.runner     = runner
        self.fb_mgr     = fb_mgr
        self.get_serial = get_serial
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        title = QLabel("Fastboot Tools")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        # ── Device info ──────────────────────────────────────
        grp_info = QGroupBox("Fastboot Device Variables")
        g = QVBoxLayout(grp_info)
        btn_read = QPushButton("⟳  Read Device Info")
        btn_read.setObjectName("primaryBtn")
        btn_read.clicked.connect(self._read_vars)
        g.addWidget(btn_read)

        self.vars_table = QTableWidget(0, 2)
        self.vars_table.setHorizontalHeaderLabels(["Variable", "Value"])
        self.vars_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.vars_table.setAlternatingRowColors(True)
        self.vars_table.setEditTriggers(QTableWidget.NoEditTriggers)
        g.addWidget(self.vars_table)
        root.addWidget(grp_info)

        # ── Bootloader ───────────────────────────────────────
        grp_bl = QGroupBox("Bootloader")
        hbl = QHBoxLayout(grp_bl)
        btn_unlock = QPushButton("🔓  Unlock Bootloader")
        btn_unlock.setObjectName("dangerBtn")
        btn_unlock.clicked.connect(self._unlock_bl)
        btn_lock = QPushButton("🔒  Lock Bootloader")
        btn_lock.setObjectName("warningBtn")
        btn_lock.clicked.connect(self._lock_bl)
        hbl.addWidget(btn_unlock)
        hbl.addWidget(btn_lock)
        root.addWidget(grp_bl)

        # ── Flash ────────────────────────────────────────────
        grp_flash = QGroupBox("Flash Partition")
        gf = QVBoxLayout(grp_flash)

        row_part = QHBoxLayout()
        row_part.addWidget(QLabel("Partition:"))
        self.partition_combo = QComboBox()
        self.partition_combo.addItems([
            "recovery", "boot", "vbmeta", "system",
            "vendor", "dtbo", "super", "userdata",
        ])
        row_part.addWidget(self.partition_combo)
        row_part.addStretch()
        gf.addLayout(row_part)

        row_img = QHBoxLayout()
        row_img.addWidget(QLabel("Image:"))
        self.img_path = QLineEdit()
        self.img_path.setPlaceholderText("Path to .img file…")
        btn_browse_img = QPushButton("Browse")
        btn_browse_img.clicked.connect(self._browse_img)
        row_img.addWidget(self.img_path, 1)
        row_img.addWidget(btn_browse_img)
        gf.addLayout(row_img)

        self.pb_flash = QProgressBar()
        self.pb_flash.setValue(0)
        gf.addWidget(self.pb_flash)

        btn_flash = QPushButton("⚡  Flash")
        btn_flash.setObjectName("dangerBtn")
        btn_flash.clicked.connect(self._flash)
        gf.addWidget(btn_flash)
        root.addWidget(grp_flash)

        # ── Reboot ───────────────────────────────────────────
        grp_reb = QGroupBox("Reboot")
        hrb = QHBoxLayout(grp_reb)
        for label, mode in [
            ("System", ""), ("Bootloader", "bootloader"),
            ("Recovery", "recovery"), ("Download", "download"),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda ch=False, m=mode: self._reboot(m))
            hrb.addWidget(btn)
        root.addWidget(grp_reb)

        # ── Log ──────────────────────────────────────────────
        self.fb_log = QPlainTextEdit()
        self.fb_log.setObjectName("logViewer")
        self.fb_log.setReadOnly(True)
        self.fb_log.setMaximumHeight(120)
        root.addWidget(self.fb_log)

    # ── Helpers ──────────────────────────────────────────────

    def _serial(self) -> str:
        s = self.get_serial()
        if not s:
            Toast.show_message(self, "No fastboot device selected!", "error")
        return s

    def _log(self, msg: str) -> None:
        self.fb_log.appendPlainText(msg)

    def _browse_img(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "IMG Files (*.img)")
        if path:
            self.img_path.setText(path)

    # ── Actions ──────────────────────────────────────────────

    def _read_vars(self) -> None:
        serial = self._serial()
        if not serial:
            return
        self.vars_table.setRowCount(0)
        self.fb_mgr.start(
            serial, "get_vars",
            on_vars=self._populate_vars,
            on_done=lambda ok, msg: self._log(msg),
        )

    def _populate_vars(self, data: dict) -> None:
        self.vars_table.setRowCount(len(data))
        for row, (k, v) in enumerate(data.items()):
            self.vars_table.setItem(row, 0, QTableWidgetItem(k))
            self.vars_table.setItem(row, 1, QTableWidgetItem(v))

    def _unlock_bl(self) -> None:
        serial = self._serial()
        if not serial:
            return
        self._log("Sending unlock command… (confirm on device)")
        self.fb_mgr.start(
            serial, "unlock",
            on_done=lambda ok, msg: (
                self._log(msg),
                Toast.show_message(self, msg, "success" if ok else "error"),
            ),
        )

    def _lock_bl(self) -> None:
        serial = self._serial()
        if not serial:
            return
        self.fb_mgr.start(
            serial, "lock",
            on_done=lambda ok, msg: (
                self._log(msg),
                Toast.show_message(self, msg, "success" if ok else "error"),
            ),
        )

    def _flash(self) -> None:
        serial = self._serial()
        if not serial:
            return
        partition = self.partition_combo.currentText()
        image     = self.img_path.text().strip()
        if not image:
            Toast.show_message(self, "Select an image file", "warning")
            return
        self.pb_flash.setValue(0)
        self.fb_mgr.start(
            serial, "flash",
            partition=partition, image=image,
            on_progress=lambda pct, msg: self.pb_flash.setValue(pct),
            on_done=lambda ok, msg: (
                self.pb_flash.setValue(100),
                self._log(msg),
                Toast.show_message(self, f"Flashed {partition}" if ok else msg,
                                   "success" if ok else "error"),
            ),
        )

    def _reboot(self, mode: str) -> None:
        serial = self._serial()
        if not serial:
            return
        self.fb_mgr.start(
            serial, "reboot", mode=mode,
            on_done=lambda ok, msg: (
                self._log(msg),
                Toast.show_message(self, msg, "info" if ok else "error"),
            ),
        )
