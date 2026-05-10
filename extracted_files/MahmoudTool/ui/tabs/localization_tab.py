"""
ui/tabs/localization_tab.py
────────────────────────────
Arabic / multi-language localization tab.
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QGroupBox, QPlainTextEdit,
    QFileDialog, QCheckBox,
)
from PySide6.QtCore import Qt, QThread

from localization.localization_tools import LocalizationTools, ARABIC_LOCALES
from adb.adb_manager import AdbRunner
from ui.widgets.toast import Toast

log = logging.getLogger(__name__)


class _LocaleWorker(QThread):
    def __init__(self, fn, *args):
        super().__init__()
        self.fn   = fn
        self.args = args
        self.result = (False, "")

    def run(self):
        try:
            self.result = self.fn(*self.args)
        except Exception as exc:
            self.result = (False, str(exc))


class LocalizationTab(QWidget):

    def __init__(self, runner: AdbRunner, get_serial, parent=None):
        super().__init__(parent)
        self.runner     = runner
        self.loc_tools  = LocalizationTools(runner)
        self.get_serial = get_serial
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("تعريب وإعداد اللغات  •  Localization")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        # ── Current locale ───────────────────────────────────
        grp_curr = QGroupBox("Current Locale")
        hc = QHBoxLayout(grp_curr)
        self.lbl_current_locale = QLabel("—")
        self.lbl_current_locale.setObjectName("infoValue")
        btn_read_locale = QPushButton("⟳ Read")
        btn_read_locale.clicked.connect(self._read_locale)
        hc.addWidget(QLabel("Current:"))
        hc.addWidget(self.lbl_current_locale, 1)
        hc.addWidget(btn_read_locale)
        root.addWidget(grp_curr)

        # ── Change locale ────────────────────────────────────
        grp_change = QGroupBox("Change Locale")
        vc = QVBoxLayout(grp_change)
        row = QHBoxLayout()
        row.addWidget(QLabel("Select Language:"))
        self.locale_combo = QComboBox()
        for code, name in ARABIC_LOCALES.items():
            self.locale_combo.addItem(f"{name}  [{code}]", code)
        row.addWidget(self.locale_combo, 1)
        vc.addLayout(row)
        btn_set_locale = QPushButton("✓  Apply Locale")
        btn_set_locale.setObjectName("primaryBtn")
        btn_set_locale.clicked.connect(self._set_locale)
        vc.addWidget(btn_set_locale)
        root.addWidget(grp_change)

        # ── Quick Arabization ─────────────────────────────────
        grp_arabic = QGroupBox("Quick Arabization")
        va = QVBoxLayout(grp_arabic)

        self.chk_samsung_arabic = QCheckBox("Samsung Arabic Enable (One UI)")
        self.chk_miui_arabic    = QCheckBox("MIUI / HyperOS Arabic Enable")
        self.chk_rtl            = QCheckBox("Apply RTL Fix")
        self.chk_carrier_unlock = QCheckBox("Unlock Carrier Language Restriction  (Verizon / AT&T)")

        for chk in (self.chk_samsung_arabic, self.chk_miui_arabic,
                    self.chk_rtl, self.chk_carrier_unlock):
            chk.setChecked(True)
            va.addWidget(chk)

        btn_arabize = QPushButton("⚡  Run Arabization")
        btn_arabize.setObjectName("successBtn")
        btn_arabize.clicked.connect(self._run_arabization)
        va.addWidget(btn_arabize)
        root.addWidget(grp_arabic)

        # ── Font Installer ───────────────────────────────────
        grp_font = QGroupBox("Arabic Font Installer  (requires root)")
        hf = QHBoxLayout(grp_font)
        self.font_path = QLabel("No font selected")
        btn_font_browse = QPushButton("Browse Font")
        btn_font_browse.clicked.connect(self._browse_font)
        self.font_path_val = ""
        btn_push_font = QPushButton("Push Font")
        btn_push_font.setObjectName("primaryBtn")
        btn_push_font.clicked.connect(self._push_font)
        hf.addWidget(self.font_path, 1)
        hf.addWidget(btn_font_browse)
        hf.addWidget(btn_push_font)
        root.addWidget(grp_font)

        # ── Hidden language activation ─────────────────────
        grp_hidden = QGroupBox("Activate Hidden Language")
        hh = QHBoxLayout(grp_hidden)
        self.hidden_locale_edit = QComboBox()
        self.hidden_locale_edit.setEditable(True)
        for code in ARABIC_LOCALES:
            self.hidden_locale_edit.addItem(code)
        btn_activate = QPushButton("Activate")
        btn_activate.setObjectName("primaryBtn")
        btn_activate.clicked.connect(self._activate_hidden)
        hh.addWidget(QLabel("Locale code:"))
        hh.addWidget(self.hidden_locale_edit, 1)
        hh.addWidget(btn_activate)
        root.addWidget(grp_hidden)

        # ── Log ──────────────────────────────────────────────
        self.loc_log = QPlainTextEdit()
        self.loc_log.setObjectName("logViewer")
        self.loc_log.setReadOnly(True)
        root.addWidget(self.loc_log, 1)

    # ── Helpers ──────────────────────────────────────────────

    def _serial(self) -> str:
        s = self.get_serial()
        if not s:
            Toast.show_message(self, "No device selected!", "error")
        return s

    def _log(self, msg: str) -> None:
        self.loc_log.appendPlainText(msg)

    def _run_in_thread(self, fn, *args, on_done=None) -> None:
        worker = _LocaleWorker(fn, *args)
        if on_done:
            worker.finished.connect(lambda: on_done(worker.result))
        worker.start()
        self._worker = worker   # keep reference

    # ── Actions ──────────────────────────────────────────────

    def _read_locale(self) -> None:
        serial = self._serial()
        if not serial:
            return
        locale = self.loc_tools.get_current_locale(serial)
        self.lbl_current_locale.setText(locale or "Unknown")

    def _set_locale(self) -> None:
        serial = self._serial()
        if not serial:
            return
        locale = self.locale_combo.currentData()
        self._run_in_thread(
            self.loc_tools.set_locale, serial, locale,
            on_done=lambda r: (
                self._log(r[1]),
                Toast.show_message(self, f"Locale set to {locale}" if r[0] else r[1],
                                   "success" if r[0] else "error"),
            ),
        )

    def _run_arabization(self) -> None:
        serial = self._serial()
        if not serial:
            return
        self._log("=== Starting Arabization ===")

        if self.chk_samsung_arabic.isChecked():
            ok, msg = self.loc_tools.enable_samsung_arabic(serial)
            self._log(f"[Samsung Arabic] {'OK' if ok else 'FAIL'}: {msg}")

        if self.chk_miui_arabic.isChecked():
            ok, msg = self.loc_tools.enable_miui_arabic(serial)
            self._log(f"[MIUI Arabic] {'OK' if ok else 'FAIL'}: {msg}")

        if self.chk_rtl.isChecked():
            ok, msg = self.loc_tools.apply_rtl_fix(serial)
            self._log(f"[RTL Fix] {'OK' if ok else 'FAIL'}: {msg}")

        if self.chk_carrier_unlock.isChecked():
            ok, msg = self.loc_tools.unlock_carrier_languages(serial)
            self._log(f"[Carrier Unlock] {'OK' if ok else 'FAIL'}: {msg}")

        self._log("=== Arabization Complete ===")
        Toast.show_message(self, "Arabization completed!", "success")

    def _browse_font(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Font", "", "Font Files (*.ttf *.otf)"
        )
        if path:
            self.font_path.setText(path.split("/")[-1].split("\\")[-1])
            self.font_path_val = path

    def _push_font(self) -> None:
        serial = self._serial()
        if not serial or not self.font_path_val:
            return
        self._run_in_thread(
            self.loc_tools.push_arabic_font, serial, self.font_path_val,
            on_done=lambda r: (
                self._log(r[1]),
                Toast.show_message(self, "Font pushed!" if r[0] else r[1],
                                   "success" if r[0] else "error"),
            ),
        )

    def _activate_hidden(self) -> None:
        serial = self._serial()
        if not serial:
            return
        locale = self.hidden_locale_edit.currentText().strip()
        self._run_in_thread(
            self.loc_tools.activate_hidden_language, serial, locale,
            on_done=lambda r: (
                self._log(r[1]),
                Toast.show_message(self, f"Activated {locale}" if r[0] else r[1],
                                   "success" if r[0] else "error"),
            ),
        )
