"""
ui/tabs/adb_tab.py
───────────────────
Full ADB operations tab.
"""

import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog,
    QTabWidget, QPlainTextEdit, QListWidget,
    QListWidgetItem, QProgressBar, QGroupBox,
    QComboBox, QCheckBox,
)
from PySide6.QtCore import Qt, Signal

from adb.adb_manager import AdbRunner, AdbThreadManager
from ui.widgets.toast import Toast

log = logging.getLogger(__name__)


class AdbTab(QWidget):
    """ADB operations: APK, files, reboot, packages, wireless, screen."""

    serial_needed = Signal()    # emitted when no device is selected

    def __init__(
        self,
        runner: AdbRunner,
        adb_mgr: AdbThreadManager,
        get_serial,             # callable -> str
        parent=None,
    ):
        super().__init__(parent)
        self.runner     = runner
        self.adb_mgr    = adb_mgr
        self.get_serial = get_serial
        self._build_ui()

    # ── UI ───────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("ADB Tools")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        tabs = QTabWidget()
        root.addWidget(tabs)

        tabs.addTab(self._build_apk_tab(),      "📦 APK Manager")
        tabs.addTab(self._build_files_tab(),     "📁 File Transfer")
        tabs.addTab(self._build_reboot_tab(),    "🔄 Reboot")
        tabs.addTab(self._build_packages_tab(),  "📋 Packages")
        tabs.addTab(self._build_wireless_tab(),  "📡 Wireless ADB")
        tabs.addTab(self._build_screen_tab(),    "🖥 Screen")
        tabs.addTab(self._build_logcat_tab(),    "📜 Logcat")

    # ── APK Tab ──────────────────────────────────────────────

    def _build_apk_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)

        grp_install = QGroupBox("Install APK")
        g = QVBoxLayout(grp_install)

        row = QHBoxLayout()
        self.apk_path_edit = QLineEdit()
        self.apk_path_edit.setPlaceholderText("Path to .apk file…")
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self._browse_apk)
        row.addWidget(self.apk_path_edit, 1)
        row.addWidget(btn_browse)
        g.addLayout(row)

        self.chk_replace   = QCheckBox("Allow version downgrade  (-d)")
        self.chk_replace.setChecked(True)
        g.addWidget(self.chk_replace)

        self.pb_apk = QProgressBar()
        self.pb_apk.setValue(0)
        g.addWidget(self.pb_apk)

        btn_install = QPushButton("▶  Install APK")
        btn_install.setObjectName("primaryBtn")
        btn_install.clicked.connect(self._install_apk)
        g.addWidget(btn_install)
        v.addWidget(grp_install)

        grp_uninstall = QGroupBox("Uninstall Package")
        g2 = QHBoxLayout(grp_uninstall)
        self.uninstall_pkg_edit = QLineEdit()
        self.uninstall_pkg_edit.setPlaceholderText("com.example.app")
        btn_uninstall = QPushButton("Uninstall")
        btn_uninstall.setObjectName("dangerBtn")
        btn_uninstall.clicked.connect(self._uninstall_pkg)
        g2.addWidget(self.uninstall_pkg_edit, 1)
        g2.addWidget(btn_uninstall)
        v.addWidget(grp_uninstall)

        self.apk_log = QPlainTextEdit()
        self.apk_log.setObjectName("logViewer")
        self.apk_log.setReadOnly(True)
        self.apk_log.setMaximumHeight(120)
        v.addWidget(self.apk_log)
        v.addStretch()
        return w

    # ── Files Tab ────────────────────────────────────────────

    def _build_files_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(12)

        # Pull
        grp_pull = QGroupBox("Pull File from Device")
        g = QGridLayout(grp_pull)
        g.addWidget(QLabel("Device path:"), 0, 0)
        self.pull_remote = QLineEdit("/sdcard/")
        g.addWidget(self.pull_remote, 0, 1)
        g.addWidget(QLabel("Save to:"), 1, 0)
        self.pull_local  = QLineEdit()
        btn_pull_browse  = QPushButton("Browse")
        btn_pull_browse.clicked.connect(lambda: self._browse_save(self.pull_local))
        g.addWidget(self.pull_local, 1, 1)
        g.addWidget(btn_pull_browse, 1, 2)
        btn_pull = QPushButton("⬇  Pull")
        btn_pull.setObjectName("primaryBtn")
        btn_pull.clicked.connect(self._pull_file)
        g.addWidget(btn_pull, 2, 0, 1, 3)
        v.addWidget(grp_pull)

        # Push
        grp_push = QGroupBox("Push File to Device")
        g2 = QGridLayout(grp_push)
        g2.addWidget(QLabel("Local file:"), 0, 0)
        self.push_local  = QLineEdit()
        btn_push_browse  = QPushButton("Browse")
        btn_push_browse.clicked.connect(
            lambda: self._browse_open(self.push_local)
        )
        g2.addWidget(self.push_local, 0, 1)
        g2.addWidget(btn_push_browse, 0, 2)
        g2.addWidget(QLabel("Device path:"), 1, 0)
        self.push_remote = QLineEdit("/sdcard/")
        g2.addWidget(self.push_remote, 1, 1, 1, 2)
        btn_push = QPushButton("⬆  Push")
        btn_push.setObjectName("primaryBtn")
        btn_push.clicked.connect(self._push_file)
        g2.addWidget(btn_push, 2, 0, 1, 3)
        v.addWidget(grp_push)

        self.file_log = QPlainTextEdit()
        self.file_log.setObjectName("logViewer")
        self.file_log.setReadOnly(True)
        self.file_log.setMaximumHeight(100)
        v.addWidget(self.file_log)
        v.addStretch()
        return w

    # ── Reboot Tab ───────────────────────────────────────────

    def _build_reboot_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(12)

        label = QLabel("Reboot Options")
        label.setObjectName("sectionTitle")
        v.addWidget(label)

        modes = [
            ("Reboot System",         "",             "primaryBtn"),
            ("Reboot Recovery",       "recovery",     "warningBtn"),
            ("Reboot Bootloader",     "bootloader",   "warningBtn"),
            ("Reboot Download Mode",  "download",     "warningBtn"),
        ]
        for text, mode, style in modes:
            btn = QPushButton(text)
            btn.setObjectName(style)
            btn.setFixedHeight(44)
            btn.clicked.connect(lambda checked=False, m=mode: self._reboot(m))
            v.addWidget(btn)

        v.addStretch()
        return w

    # ── Packages Tab ─────────────────────────────────────────

    def _build_packages_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(8)

        hdr = QHBoxLayout()
        lbl = QLabel("Installed Packages")
        lbl.setObjectName("sectionTitle")
        self.pkg_filter = QComboBox()
        self.pkg_filter.addItems(["All", "System", "User", "Disabled"])
        btn_refresh = QPushButton("⟳ Refresh")
        btn_refresh.clicked.connect(self._load_packages)
        hdr.addWidget(lbl)
        hdr.addStretch()
        hdr.addWidget(self.pkg_filter)
        hdr.addWidget(btn_refresh)
        v.addLayout(hdr)

        self.pkg_search = QLineEdit()
        self.pkg_search.setPlaceholderText("Search packages…")
        self.pkg_search.textChanged.connect(self._filter_packages)
        v.addWidget(self.pkg_search)

        self.pkg_list = QListWidget()
        v.addWidget(self.pkg_list, 1)

        pkg_btns = QHBoxLayout()
        btn_disable = QPushButton("Disable Selected")
        btn_disable.setObjectName("warningBtn")
        btn_disable.clicked.connect(self._disable_selected)
        btn_enable = QPushButton("Enable Selected")
        btn_enable.setObjectName("successBtn")
        btn_enable.clicked.connect(self._enable_selected)
        btn_uninstall2 = QPushButton("Uninstall Selected")
        btn_uninstall2.setObjectName("dangerBtn")
        btn_uninstall2.clicked.connect(self._uninstall_selected)
        pkg_btns.addWidget(btn_disable)
        pkg_btns.addWidget(btn_enable)
        pkg_btns.addWidget(btn_uninstall2)
        v.addLayout(pkg_btns)
        return w

    # ── Wireless ADB Tab ─────────────────────────────────────

    def _build_wireless_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(12)

        lbl = QLabel("Wireless ADB")
        lbl.setObjectName("sectionTitle")
        v.addWidget(lbl)

        grp = QGroupBox("Enable TCP/IP on connected device")
        g = QVBoxLayout(grp)
        row = QHBoxLayout()
        row.addWidget(QLabel("Port:"))
        self.wireless_port = QLineEdit("5555")
        self.wireless_port.setFixedWidth(80)
        row.addWidget(self.wireless_port)
        row.addStretch()
        g.addLayout(row)
        btn_enable_tcp = QPushButton("Enable TCP/IP")
        btn_enable_tcp.setObjectName("primaryBtn")
        btn_enable_tcp.clicked.connect(self._enable_tcpip)
        g.addWidget(btn_enable_tcp)
        v.addWidget(grp)

        grp2 = QGroupBox("Connect to wireless device")
        g2 = QVBoxLayout(grp2)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("IP:"))
        self.wireless_ip = QLineEdit()
        self.wireless_ip.setPlaceholderText("192.168.1.x")
        row2.addWidget(self.wireless_ip, 1)
        row2.addWidget(QLabel("Port:"))
        self.wireless_port2 = QLineEdit("5555")
        self.wireless_port2.setFixedWidth(80)
        row2.addWidget(self.wireless_port2)
        g2.addLayout(row2)
        btn_connect = QPushButton("Connect")
        btn_connect.setObjectName("primaryBtn")
        btn_connect.clicked.connect(self._connect_wireless)
        g2.addWidget(btn_connect)
        v.addWidget(grp2)

        self.wireless_log = QPlainTextEdit()
        self.wireless_log.setObjectName("logViewer")
        self.wireless_log.setReadOnly(True)
        self.wireless_log.setMaximumHeight(80)
        v.addWidget(self.wireless_log)
        v.addStretch()
        return w

    # ── Screen Tab ───────────────────────────────────────────

    def _build_screen_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(12)

        lbl = QLabel("Screen Tools")
        lbl.setObjectName("sectionTitle")
        v.addWidget(lbl)

        btn_ss = QPushButton("📸  Screenshot")
        btn_ss.setObjectName("primaryBtn")
        btn_ss.setFixedHeight(44)
        btn_ss.clicked.connect(self._screenshot)
        v.addWidget(btn_ss)

        btn_scrcpy = QPushButton("🖥  Launch SCRCPY")
        btn_scrcpy.setFixedHeight(44)
        btn_scrcpy.clicked.connect(self._launch_scrcpy)
        v.addWidget(btn_scrcpy)

        v.addStretch()
        return w

    # ── Logcat Tab ───────────────────────────────────────────

    def _build_logcat_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(8)

        hdr = QHBoxLayout()
        lbl = QLabel("Logcat Viewer")
        lbl.setObjectName("sectionTitle")
        btn_refresh_lc = QPushButton("⟳ Fetch")
        btn_refresh_lc.clicked.connect(self._fetch_logcat)
        btn_clear_lc = QPushButton("Clear")
        btn_clear_lc.clicked.connect(lambda: self.logcat_view.clear())
        hdr.addWidget(lbl)
        hdr.addStretch()
        hdr.addWidget(btn_refresh_lc)
        hdr.addWidget(btn_clear_lc)
        v.addLayout(hdr)

        self.logcat_view = QPlainTextEdit()
        self.logcat_view.setObjectName("logViewer")
        self.logcat_view.setReadOnly(True)
        v.addWidget(self.logcat_view, 1)
        return w

    # ── Actions ──────────────────────────────────────────────

    def _serial(self) -> str:
        s = self.get_serial()
        if not s:
            Toast.show_message(self, "No device selected!", "error")
        return s

    def _browse_apk(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select APK", "", "APK Files (*.apk)")
        if path:
            self.apk_path_edit.setText(path)

    def _browse_save(self, edit: QLineEdit) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if path:
            edit.setText(path)

    def _browse_open(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if path:
            edit.setText(path)

    def _install_apk(self) -> None:
        serial = self._serial()
        if not serial:
            return
        apk = self.apk_path_edit.text().strip()
        if not apk:
            Toast.show_message(self, "Choose an APK file first", "warning")
            return
        self.pb_apk.setValue(0)
        self.adb_mgr.start(
            serial, "install_apk", apk_path=apk,
            on_done=lambda ok, msg: self._on_apk_done(ok, msg),
            on_progress=lambda pct, msg: self.pb_apk.setValue(pct),
        )

    def _on_apk_done(self, ok: bool, msg: str) -> None:
        self.pb_apk.setValue(100)
        self.apk_log.appendPlainText(msg)
        Toast.show_message(self, "APK Installed!" if ok else f"Failed: {msg}",
                           "success" if ok else "error")

    def _uninstall_pkg(self) -> None:
        serial = self._serial()
        if not serial:
            return
        pkg = self.uninstall_pkg_edit.text().strip()
        if not pkg:
            return
        self.adb_mgr.start(
            serial, "uninstall", package=pkg,
            on_done=lambda ok, msg: (
                self.apk_log.appendPlainText(msg),
                Toast.show_message(self, "Uninstalled" if ok else msg,
                                   "success" if ok else "error"),
            ),
        )

    def _pull_file(self) -> None:
        serial = self._serial()
        if not serial:
            return
        self.adb_mgr.start(
            serial, "pull",
            remote=self.pull_remote.text(),
            local=self.pull_local.text(),
            on_done=lambda ok, msg: (
                self.file_log.appendPlainText(msg),
                Toast.show_message(self, "Pulled!" if ok else msg,
                                   "success" if ok else "error"),
            ),
        )

    def _push_file(self) -> None:
        serial = self._serial()
        if not serial:
            return
        self.adb_mgr.start(
            serial, "push",
            local=self.push_local.text(),
            remote=self.push_remote.text(),
            on_done=lambda ok, msg: (
                self.file_log.appendPlainText(msg),
                Toast.show_message(self, "Pushed!" if ok else msg,
                                   "success" if ok else "error"),
            ),
        )

    def _reboot(self, mode: str) -> None:
        serial = self._serial()
        if not serial:
            return
        label = mode or "system"
        self.adb_mgr.start(
            serial, "reboot", mode=mode,
            on_done=lambda ok, msg: Toast.show_message(
                self, f"Rebooting to {label}…" if ok else msg,
                "info" if ok else "error",
            ),
        )

    def _load_packages(self) -> None:
        serial = self._serial()
        if not serial:
            return
        flags_map = {
            "All": "", "System": "-s", "User": "-3", "Disabled": "-d"
        }
        flags = flags_map.get(self.pkg_filter.currentText(), "")
        self.adb_mgr.start(
            serial, "get_packages", flags=flags,
            on_done=self._on_packages_loaded,
        )

    def _on_packages_loaded(self, ok: bool, msg: str) -> None:
        self.pkg_list.clear()
        if ok:
            for pkg in msg.splitlines():
                if pkg.strip():
                    self.pkg_list.addItem(pkg.strip())

    def _filter_packages(self, text: str) -> None:
        for i in range(self.pkg_list.count()):
            item = self.pkg_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def _disable_selected(self) -> None:
        serial = self._serial()
        if not serial:
            return
        for item in self.pkg_list.selectedItems():
            pkg = item.text()
            self.runner.shell(serial, f"pm disable-user --user 0 {pkg}")
        Toast.show_message(self, "Selected packages disabled", "warning")

    def _enable_selected(self) -> None:
        serial = self._serial()
        if not serial:
            return
        for item in self.pkg_list.selectedItems():
            pkg = item.text()
            self.runner.shell(serial, f"pm enable {pkg}")
        Toast.show_message(self, "Selected packages enabled", "success")

    def _uninstall_selected(self) -> None:
        serial = self._serial()
        if not serial:
            return
        for item in self.pkg_list.selectedItems():
            pkg = item.text()
            self.adb_mgr.start(serial, "uninstall", package=pkg,
                               on_done=lambda ok, msg: None)
        Toast.show_message(self, "Uninstall queued", "warning")

    def _enable_tcpip(self) -> None:
        serial = self._serial()
        if not serial:
            return
        port = int(self.wireless_port.text() or "5555")
        ok, msg = self.runner.enable_tcpip(serial, port)
        self.wireless_log.appendPlainText(msg)
        Toast.show_message(self, msg, "success" if ok else "error")

    def _connect_wireless(self) -> None:
        ip   = self.wireless_ip.text().strip()
        port = int(self.wireless_port2.text() or "5555")
        ok, msg = self.runner.connect_wireless(ip, port)
        self.wireless_log.appendPlainText(msg)
        Toast.show_message(self, msg, "success" if ok else "error")

    def _screenshot(self) -> None:
        serial = self._serial()
        if not serial:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Screenshot", "screenshot.png", "PNG (*.png)"
        )
        if not path:
            return
        self.adb_mgr.start(
            serial, "screenshot", save_path=path,
            on_done=lambda ok, msg: Toast.show_message(
                self, f"Saved to {path}" if ok else msg,
                "success" if ok else "error",
            ),
        )

    def _launch_scrcpy(self) -> None:
        serial = self._serial()
        if not serial:
            return
        import subprocess, os
        try:
            subprocess.Popen(
                ["scrcpy", "-s", serial],
                creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
            )
        except FileNotFoundError:
            Toast.show_message(self, "scrcpy not found in PATH", "error")

    def _fetch_logcat(self) -> None:
        serial = self._serial()
        if not serial:
            return
        lines = self.runner.get_logcat_lines(serial, 300)
        self.logcat_view.setPlainText(lines)
