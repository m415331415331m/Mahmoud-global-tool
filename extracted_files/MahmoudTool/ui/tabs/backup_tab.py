"""
ui/tabs/backup_tab.py
──────────────────────
Complete Backup & Restore tab.
"""

import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QPlainTextEdit,
    QProgressBar, QFileDialog, QListWidget,
    QListWidgetItem, QCheckBox, QTabWidget,
)
from PySide6.QtCore import Qt

from core.backup_manager import BackupManager
from ui.widgets.toast import Toast

log = logging.getLogger(__name__)


class BackupTab(QWidget):

    def __init__(self, backup_mgr: BackupManager, get_serial, parent=None):
        super().__init__(parent)
        self.backup_mgr = backup_mgr
        self.get_serial = get_serial
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("النسخ الاحتياطي والاستعادة  •  Backup & Restore")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        tabs = QTabWidget()
        root.addWidget(tabs)

        tabs.addTab(self._build_adb_backup_tab(),  "💾 ADB Backup")
        tabs.addTab(self._build_pull_tab(),         "📁 Pull Files")
        tabs.addTab(self._build_restore_tab(),      "↩ Restore")
        tabs.addTab(self._build_history_tab(),      "📋 History")

    # ── ADB Backup ────────────────────────────────────────────

    def _build_adb_backup_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)

        grp = QGroupBox("ADB Full Backup")
        g = QVBoxLayout(grp)

        # Options
        self.chk_apk    = QCheckBox("Include APK files")
        self.chk_shared = QCheckBox("Include shared storage (SD Card)")
        self.chk_system = QCheckBox("Include system apps (requires confirmation)")
        self.chk_apk.setChecked(True)
        self.chk_shared.setChecked(True)
        for chk in (self.chk_apk, self.chk_shared, self.chk_system):
            g.addWidget(chk)

        # Destination
        dest_row = QHBoxLayout()
        self.backup_dest_lbl = QLabel("No destination selected")
        self.backup_dest_lbl.setObjectName("infoKey")
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self._browse_backup_dest)
        self.backup_dest_path = ""
        dest_row.addWidget(self.backup_dest_lbl, 1)
        dest_row.addWidget(btn_browse)
        g.addLayout(dest_row)

        self.pb_backup = QProgressBar()
        g.addWidget(self.pb_backup)

        btn_start = QPushButton("▶  Start ADB Backup")
        btn_start.setObjectName("primaryBtn")
        btn_start.setFixedHeight(42)
        btn_start.clicked.connect(self._start_backup)
        g.addWidget(btn_start)

        note = QLabel(
            "⚠ After clicking Start, confirm backup on your device screen.\n"
            "Android 12+ may limit what can be backed up via ADB."
        )
        note.setStyleSheet("color: #E3B341; font-size: 11px;")
        note.setWordWrap(True)
        g.addWidget(note)
        v.addWidget(grp)

        self.backup_log = QPlainTextEdit()
        self.backup_log.setObjectName("logViewer")
        self.backup_log.setReadOnly(True)
        v.addWidget(self.backup_log, 1)
        return w

    # ── Pull Files ────────────────────────────────────────────

    def _build_pull_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)

        grp = QGroupBox("Pull Folders from Device")
        g = QVBoxLayout(grp)

        folders = [
            "/sdcard/DCIM",
            "/sdcard/Pictures",
            "/sdcard/Downloads",
            "/sdcard/Documents",
            "/sdcard/WhatsApp",
            "/sdcard/Telegram",
            "/sdcard/Music",
            "/sdcard/Movies",
        ]
        self.folder_checks: dict[str, QCheckBox] = {}
        for folder in folders:
            chk = QCheckBox(folder)
            chk.setChecked(True)
            g.addWidget(chk)
            self.folder_checks[folder] = chk

        dest_row = QHBoxLayout()
        self.pull_dest_lbl = QLabel("No destination selected")
        btn_browse_pull = QPushButton("Browse")
        btn_browse_pull.clicked.connect(self._browse_pull_dest)
        self.pull_dest_path = ""
        dest_row.addWidget(self.pull_dest_lbl, 1)
        dest_row.addWidget(btn_browse_pull)
        g.addLayout(dest_row)

        self.pb_pull = QProgressBar()
        g.addWidget(self.pb_pull)

        btn_pull = QPushButton("⬇  Pull Selected Folders")
        btn_pull.setObjectName("primaryBtn")
        btn_pull.setFixedHeight(42)
        btn_pull.clicked.connect(self._start_pull)
        g.addWidget(btn_pull)
        v.addWidget(grp)

        self.pull_log = QPlainTextEdit()
        self.pull_log.setObjectName("logViewer")
        self.pull_log.setReadOnly(True)
        v.addWidget(self.pull_log, 1)
        return w

    # ── Restore ───────────────────────────────────────────────

    def _build_restore_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)

        grp = QGroupBox("ADB Restore")
        g = QVBoxLayout(grp)

        file_row = QHBoxLayout()
        self.restore_file_lbl = QLabel("No backup file selected")
        self.restore_file_path = ""
        btn_browse_ab = QPushButton("Browse .ab")
        btn_browse_ab.clicked.connect(self._browse_restore_file)
        file_row.addWidget(self.restore_file_lbl, 1)
        file_row.addWidget(btn_browse_ab)
        g.addLayout(file_row)

        self.pb_restore = QProgressBar()
        g.addWidget(self.pb_restore)

        btn_restore = QPushButton("↩  Start Restore")
        btn_restore.setObjectName("warningBtn")
        btn_restore.setFixedHeight(42)
        btn_restore.clicked.connect(self._start_restore)
        g.addWidget(btn_restore)

        note = QLabel("⚠ Confirm restore on device screen when prompted.")
        note.setStyleSheet("color: #E3B341; font-size: 11px;")
        g.addWidget(note)
        v.addWidget(grp)

        self.restore_log = QPlainTextEdit()
        self.restore_log.setObjectName("logViewer")
        self.restore_log.setReadOnly(True)
        v.addWidget(self.restore_log, 1)
        return w

    # ── History ───────────────────────────────────────────────

    def _build_history_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(8)

        hdr = QHBoxLayout()
        lbl = QLabel("Backup Files")
        lbl.setObjectName("sectionTitle")
        btn_refresh = QPushButton("⟳ Refresh")
        btn_refresh.clicked.connect(self._load_history)
        hdr.addWidget(lbl)
        hdr.addStretch()
        hdr.addWidget(btn_refresh)
        v.addLayout(hdr)

        self.history_list = QListWidget()
        v.addWidget(self.history_list, 1)

        self._load_history()
        return w

    def _load_history(self) -> None:
        self.history_list.clear()
        for p in self.backup_mgr.list_backups():
            size_mb = p.stat().st_size // (1024 * 1024)
            item = QListWidgetItem(f"💾  {p.name}  ({size_mb} MB)")
            item.setData(Qt.UserRole, str(p))
            self.history_list.addItem(item)

    # ── Helpers ──────────────────────────────────────────────

    def _serial(self) -> str:
        s = self.get_serial()
        if not s:
            Toast.show_message(self, "No device selected!", "error")
        return s

    def _browse_backup_dest(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Backup destination", "backup.ab", "ADB Backup (*.ab)"
        )
        if path:
            self.backup_dest_path = path
            self.backup_dest_lbl.setText(path)

    def _browse_pull_dest(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select destination folder")
        if path:
            self.pull_dest_path = path
            self.pull_dest_lbl.setText(path)

    def _browse_restore_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select backup file", "", "ADB Backup (*.ab)"
        )
        if path:
            self.restore_file_path = path
            self.restore_file_lbl.setText(path)

    # ── Actions ──────────────────────────────────────────────

    def _start_backup(self) -> None:
        serial = self._serial()
        if not serial:
            return
        if not self.backup_dest_path:
            self.backup_dest_path = self.backup_mgr.default_backup_path(serial)
            self.backup_dest_lbl.setText(self.backup_dest_path)

        self.pb_backup.setValue(0)
        options = {
            "apk":    self.chk_apk.isChecked(),
            "shared": self.chk_shared.isChecked(),
            "system": self.chk_system.isChecked(),
            "all":    True,
        }
        self.backup_mgr.start_backup(
            serial,
            output_path=self.backup_dest_path,
            options=options,
            on_progress=lambda pct, msg: (
                self.pb_backup.setValue(pct),
                self.backup_log.appendPlainText(msg),
            ),
            on_done=lambda ok, msg: (
                self.pb_backup.setValue(100),
                self.backup_log.appendPlainText(msg),
                Toast.show_message(
                    self,
                    "Backup complete!" if ok else f"Backup failed: {msg[:60]}",
                    "success" if ok else "error",
                ),
                self._load_history(),
            ),
            on_log=lambda line: self.backup_log.appendPlainText(line),
        )

    def _start_pull(self) -> None:
        serial = self._serial()
        if not serial:
            return
        if not self.pull_dest_path:
            Toast.show_message(self, "Select destination folder first", "warning")
            return

        folders = [f for f, chk in self.folder_checks.items() if chk.isChecked()]
        if not folders:
            Toast.show_message(self, "Select at least one folder", "warning")
            return

        self.pb_pull.setValue(0)
        self.backup_mgr.start_pull_backup(
            serial,
            dest_dir=self.pull_dest_path,
            folders=folders,
            on_progress=lambda pct, msg: self.pb_pull.setValue(pct),
            on_done=lambda ok, msg: (
                self.pb_pull.setValue(100),
                Toast.show_message(self, "Pull complete!" if ok else msg,
                                   "success" if ok else "error"),
            ),
            on_log=lambda line: self.pull_log.appendPlainText(line),
        )

    def _start_restore(self) -> None:
        serial = self._serial()
        if not serial or not self.restore_file_path:
            Toast.show_message(self, "Select a backup file first", "warning")
            return

        self.pb_restore.setValue(0)
        self.backup_mgr.start_restore(
            serial,
            backup_path=self.restore_file_path,
            on_progress=lambda pct, msg: self.pb_restore.setValue(pct),
            on_done=lambda ok, msg: (
                self.pb_restore.setValue(100),
                Toast.show_message(self, "Restore complete!" if ok else msg,
                                   "success" if ok else "error"),
            ),
            on_log=lambda line: self.restore_log.appendPlainText(line),
        )
