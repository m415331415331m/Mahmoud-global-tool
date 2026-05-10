"""
ui/tabs/settings_tab.py
────────────────────────
Application settings: paths, language, update channel, ADB options.
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QLineEdit,
    QComboBox, QCheckBox, QFileDialog,
)
from PySide6.QtCore import Qt

from core.config import AppConfig
from ui.widgets.toast import Toast

log = logging.getLogger(__name__)

LANGUAGES = {
    "ar": "العربية",
    "en": "English",
    "tr": "Türkçe",
    "fr": "Français",
    "de": "Deutsch",
}


class SettingsTab(QWidget):

    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._build_ui()
        self._load_from_config()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        title = QLabel("الإعدادات  •  Settings")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        # ── Language ─────────────────────────────────────────
        grp_lang = QGroupBox("Language / اللغة")
        gl = QHBoxLayout(grp_lang)
        gl.addWidget(QLabel("Interface Language:"))
        self.lang_combo = QComboBox()
        for code, name in LANGUAGES.items():
            self.lang_combo.addItem(name, code)
        gl.addWidget(self.lang_combo)
        gl.addStretch()
        root.addWidget(grp_lang)

        # ── Tool Paths ───────────────────────────────────────
        grp_paths = QGroupBox("Tool Paths")
        gp = QVBoxLayout(grp_paths)

        def _path_row(label: str, attr: str) -> QLineEdit:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{label}:"))
            edit = QLineEdit()
            edit.setObjectName(attr)
            btn = QPushButton("Browse")
            btn.clicked.connect(lambda _, e=edit: self._browse_binary(e))
            row.addWidget(edit, 1)
            row.addWidget(btn)
            gp.addLayout(row)
            return edit

        self.adb_path_edit      = _path_row("ADB Binary",    "adb_path")
        self.fastboot_path_edit = _path_row("Fastboot Binary","fastboot_path")
        self.scrcpy_path_edit   = _path_row("SCRCPY Binary",  "scrcpy_path")
        root.addWidget(grp_paths)

        # ── ADB Options ──────────────────────────────────────
        grp_adb = QGroupBox("ADB Options")
        ga = QVBoxLayout(grp_adb)
        self.chk_auto_detect = QCheckBox("Auto-detect devices on startup")
        self.chk_notifications = QCheckBox("Show toast notifications")
        ga.addWidget(self.chk_auto_detect)
        ga.addWidget(self.chk_notifications)

        row_interval = QHBoxLayout()
        row_interval.addWidget(QLabel("Device refresh interval (ms):"))
        self.interval_edit = QLineEdit()
        self.interval_edit.setFixedWidth(80)
        row_interval.addWidget(self.interval_edit)
        row_interval.addStretch()
        ga.addLayout(row_interval)
        root.addWidget(grp_adb)

        # ── Update channel ───────────────────────────────────
        grp_update = QGroupBox("Update Channel")
        gu = QHBoxLayout(grp_update)
        gu.addWidget(QLabel("Channel:"))
        self.update_combo = QComboBox()
        self.update_combo.addItems(["stable", "beta", "nightly"])
        gu.addWidget(self.update_combo)
        gu.addStretch()
        root.addWidget(grp_update)

        # ── Save ─────────────────────────────────────────────
        btn_save = QPushButton("💾  Save Settings")
        btn_save.setObjectName("primaryBtn")
        btn_save.setFixedHeight(42)
        btn_save.clicked.connect(self._save)
        root.addWidget(btn_save)

        root.addStretch()

    # ── Helpers ──────────────────────────────────────────────

    def _load_from_config(self) -> None:
        # Language
        idx = self.lang_combo.findData(self.config.language or "ar")
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)

        # Paths
        self.adb_path_edit.setText(self.config.adb_path or "adb")
        self.fastboot_path_edit.setText(self.config.fastboot_path or "fastboot")
        self.scrcpy_path_edit.setText(self.config.scrcpy_path or "scrcpy")

        # ADB opts
        self.chk_auto_detect.setChecked(bool(self.config.auto_detect_device))
        self.chk_notifications.setChecked(bool(self.config.show_notifications))
        self.interval_edit.setText(str(self.config.refresh_interval_ms or 2000))

        # Update channel
        idx = self.update_combo.findText(self.config.update_channel or "stable")
        if idx >= 0:
            self.update_combo.setCurrentIndex(idx)

    def _browse_binary(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Binary", "",
            "Executables (*.exe);;All Files (*)"
        )
        if path:
            edit.setText(path)

    def _save(self) -> None:
        self.config.set("language",           self.lang_combo.currentData())
        self.config.set("adb_path",           self.adb_path_edit.text().strip() or "adb")
        self.config.set("fastboot_path",      self.fastboot_path_edit.text().strip() or "fastboot")
        self.config.set("scrcpy_path",        self.scrcpy_path_edit.text().strip() or "scrcpy")
        self.config.set("auto_detect_device", self.chk_auto_detect.isChecked())
        self.config.set("show_notifications", self.chk_notifications.isChecked())
        self.config.set("update_channel",     self.update_combo.currentText())

        try:
            interval = int(self.interval_edit.text())
            self.config.set("refresh_interval_ms", interval)
        except ValueError:
            pass

        Toast.show_message(self, "Settings saved!", "success")
