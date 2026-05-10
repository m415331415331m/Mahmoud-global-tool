"""
core/tools_downloader.py
─────────────────────────
Downloads official Google Platform Tools (ADB + Fastboot) once.
Source: https://dl.google.com/android/repository/platform-tools-latest-windows.zip
"""

import os
import zipfile
import logging
import hashlib
import urllib.request
from pathlib import Path
from PySide6.QtCore import QThread, Signal

log = logging.getLogger(__name__)

PLATFORM_TOOLS_URL = (
    "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
)
EXPECTED_FILES = ["adb.exe", "fastboot.exe", "AdbWinApi.dll", "AdbWinUsbApi.dll"]


class DownloadWorker(QThread):
    """Downloads platform-tools in background thread."""

    progress  = Signal(int, str)   # percent, message
    finished  = Signal(bool, str)  # success, message

    def __init__(self, dest_dir: Path) -> None:
        super().__init__()
        self.dest_dir = dest_dir

    def run(self) -> None:
        dest = self.dest_dir
        dest.mkdir(parents=True, exist_ok=True)
        zip_path = dest / "platform-tools.zip"

        try:
            self.progress.emit(5, "Connecting to Google servers…")

            # ── Download ──────────────────────────────────────
            def _hook(block_count, block_size, total):
                if total > 0:
                    pct = min(int(block_count * block_size / total * 80), 80)
                    mb = block_count * block_size / 1_048_576
                    self.progress.emit(pct, f"Downloading… {mb:.1f} MB")

            urllib.request.urlretrieve(PLATFORM_TOOLS_URL, zip_path, _hook)
            self.progress.emit(82, "Download complete. Extracting…")

            # ── Extract ───────────────────────────────────────
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(dest)

            # Move files up from platform-tools/ subfolder
            pt_dir = dest / "platform-tools"
            if pt_dir.exists():
                for f in pt_dir.iterdir():
                    target = dest / f.name
                    if not target.exists():
                        f.rename(target)
                pt_dir.rmdir() if not any(pt_dir.iterdir()) else None

            self.progress.emit(95, "Cleaning up…")
            zip_path.unlink(missing_ok=True)

            # ── Verify ────────────────────────────────────────
            missing = [f for f in EXPECTED_FILES if not (dest / f).exists()]
            if missing:
                self.finished.emit(False, f"Missing files: {', '.join(missing)}")
                return

            self.progress.emit(100, "Platform tools ready!")
            self.finished.emit(True, str(dest))

        except Exception as exc:
            log.exception("Download failed: %s", exc)
            self.finished.emit(False, str(exc))


class PlatformToolsManager:
    """Check and manage ADB/Fastboot availability."""

    def __init__(self, tools_dir: Path) -> None:
        self.tools_dir = tools_dir

    def is_installed(self) -> bool:
        return all((self.tools_dir / f).exists() for f in ["adb.exe", "fastboot.exe"])

    def get_adb_path(self) -> str:
        local = self.tools_dir / "adb.exe"
        return str(local) if local.exists() else "adb"

    def get_fastboot_path(self) -> str:
        local = self.tools_dir / "fastboot.exe"
        return str(local) if local.exists() else "fastboot"

    def get_version(self) -> str:
        """Return ADB version string."""
        import subprocess
        adb = self.get_adb_path()
        try:
            r = subprocess.run(
                [adb, "version"], capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            for line in r.stdout.splitlines():
                if "Android Debug Bridge" in line:
                    return line.strip()
        except Exception:
            pass
        return "Unknown"

    def start_download(self, on_progress=None, on_done=None) -> DownloadWorker:
        worker = DownloadWorker(self.tools_dir)
        if on_progress:
            worker.progress.connect(on_progress)
        if on_done:
            worker.finished.connect(on_done)
        worker.start()
        return worker
