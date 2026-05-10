"""
core/backup_manager.py
───────────────────────
Full backup and restore system using ADB official commands.
Supports: APKs, user data, contacts, SMS, media files.
"""

import os
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from PySide6.QtCore import QThread, Signal

log = logging.getLogger(__name__)


class BackupWorker(QThread):
    """Runs ADB backup in background thread."""

    progress = Signal(int, str)
    finished = Signal(bool, str)
    log_line = Signal(str)

    def __init__(
        self,
        adb_path: str,
        serial: str,
        output_path: str,
        options: dict,
    ):
        super().__init__()
        self.adb_path    = adb_path
        self.serial      = serial
        self.output_path = output_path
        self.options     = options   # {apk, shared, system, all}

    def run(self):
        try:
            self.progress.emit(10, "Preparing backup command…")

            cmd = [self.adb_path, "-s", self.serial, "backup"]

            if self.options.get("apk",    True):  cmd.append("-apk")
            if self.options.get("shared", True):   cmd.append("-shared")
            if self.options.get("system", False):  cmd.append("-system")
            if self.options.get("all",    True):   cmd.append("-all")

            cmd += ["-f", self.output_path]

            self.log_line.emit(f"Running: {' '.join(cmd)}")
            self.log_line.emit("⚠ Confirm backup on your device screen…")
            self.progress.emit(20, "Waiting for device confirmation…")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                ),
            )

            if result.returncode == 0:
                size = Path(self.output_path).stat().st_size // 1024
                self.progress.emit(100, f"Backup complete ({size} KB)")
                self.finished.emit(True, self.output_path)
            else:
                self.finished.emit(False, result.stderr or "Backup failed")

        except subprocess.TimeoutExpired:
            self.finished.emit(False, "Backup timed out (10 min limit)")
        except Exception as exc:
            self.finished.emit(False, str(exc))


class RestoreWorker(QThread):
    """Runs ADB restore in background thread."""

    progress = Signal(int, str)
    finished = Signal(bool, str)
    log_line = Signal(str)

    def __init__(self, adb_path: str, serial: str, backup_path: str):
        super().__init__()
        self.adb_path    = adb_path
        self.serial      = serial
        self.backup_path = backup_path

    def run(self):
        try:
            self.progress.emit(10, "Starting restore…")
            self.log_line.emit("⚠ Confirm restore on your device screen…")

            cmd = [
                self.adb_path, "-s", self.serial,
                "restore", self.backup_path,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                ),
            )

            if result.returncode == 0:
                self.progress.emit(100, "Restore complete")
                self.finished.emit(True, "Restore completed successfully")
            else:
                self.finished.emit(False, result.stderr or "Restore failed")

        except subprocess.TimeoutExpired:
            self.finished.emit(False, "Restore timed out")
        except Exception as exc:
            self.finished.emit(False, str(exc))


class PullBackupWorker(QThread):
    """Pull specific folders from device using adb pull."""

    progress = Signal(int, str)
    finished = Signal(bool, str)
    log_line = Signal(str)

    FOLDERS = [
        "/sdcard/DCIM",
        "/sdcard/Pictures",
        "/sdcard/Downloads",
        "/sdcard/Documents",
        "/sdcard/WhatsApp",
        "/sdcard/Telegram",
    ]

    def __init__(
        self,
        adb_path: str,
        serial: str,
        dest_dir: str,
        folders: list[str] | None = None,
    ):
        super().__init__()
        self.adb_path = adb_path
        self.serial   = serial
        self.dest_dir = dest_dir
        self.folders  = folders or self.FOLDERS

    def run(self):
        dest = Path(self.dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        total = len(self.folders)

        for i, folder in enumerate(self.folders):
            name = folder.split("/")[-1]
            self.progress.emit(int(i / total * 90), f"Pulling {name}…")
            self.log_line.emit(f"  → {folder}")

            try:
                result = subprocess.run(
                    [self.adb_path, "-s", self.serial, "pull", folder, str(dest)],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    creationflags=(
                        subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                    ),
                )
                self.log_line.emit(
                    f"    {'✓' if result.returncode == 0 else '✗'} {result.stdout.strip()[:80]}"
                )
            except Exception as exc:
                self.log_line.emit(f"    ✗ {exc}")

        self.progress.emit(100, "Pull backup complete")
        self.finished.emit(True, str(dest))


class BackupManager:
    """
    High-level backup manager.
    Provides factory methods for all backup/restore operations.
    """

    def __init__(self, adb_path: str, backups_dir: Path):
        self.adb_path    = adb_path
        self.backups_dir = backups_dir
        backups_dir.mkdir(parents=True, exist_ok=True)

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def default_backup_path(self, serial: str) -> str:
        fname = f"backup_{serial}_{self._timestamp()}.ab"
        return str(self.backups_dir / fname)

    def start_backup(
        self,
        serial: str,
        output_path: str | None = None,
        options: dict | None = None,
        on_progress=None,
        on_done=None,
        on_log=None,
    ) -> BackupWorker:
        path    = output_path or self.default_backup_path(serial)
        options = options or {"apk": True, "shared": True, "system": False, "all": True}

        worker = BackupWorker(self.adb_path, serial, path, options)
        if on_progress: worker.progress.connect(on_progress)
        if on_done:     worker.finished.connect(on_done)
        if on_log:      worker.log_line.connect(on_log)
        worker.start()
        return worker

    def start_restore(
        self,
        serial: str,
        backup_path: str,
        on_progress=None,
        on_done=None,
        on_log=None,
    ) -> RestoreWorker:
        worker = RestoreWorker(self.adb_path, serial, backup_path)
        if on_progress: worker.progress.connect(on_progress)
        if on_done:     worker.finished.connect(on_done)
        if on_log:      worker.log_line.connect(on_log)
        worker.start()
        return worker

    def start_pull_backup(
        self,
        serial: str,
        dest_dir: str | None = None,
        folders: list[str] | None = None,
        on_progress=None,
        on_done=None,
        on_log=None,
    ) -> PullBackupWorker:
        dest = dest_dir or str(
            self.backups_dir / f"pull_{serial}_{self._timestamp()}"
        )
        worker = PullBackupWorker(self.adb_path, serial, dest, folders)
        if on_progress: worker.progress.connect(on_progress)
        if on_done:     worker.finished.connect(on_done)
        if on_log:      worker.log_line.connect(on_log)
        worker.start()
        return worker

    def list_backups(self) -> list[Path]:
        return sorted(self.backups_dir.glob("*.ab"), key=lambda p: p.stat().st_mtime, reverse=True)
