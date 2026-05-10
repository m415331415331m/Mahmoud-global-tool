"""
adb/sideload_manager.py
────────────────────────
Official ADB Sideload for OTA updates and official firmware packages.
Uses only: adb sideload (official Android command).
"""

import os
import logging
import subprocess
from pathlib import Path
from PySide6.QtCore import QThread, Signal

log = logging.getLogger(__name__)


class SideloadWorker(QThread):
    """
    Runs adb sideload in background.
    Device must be in Recovery mode with sideload option selected.
    """

    progress = Signal(int, str)
    finished = Signal(bool, str)
    log_line = Signal(str)

    def __init__(self, adb_path: str, serial: str, zip_path: str):
        super().__init__()
        self.adb_path = adb_path
        self.serial   = serial
        self.zip_path = zip_path

    def run(self) -> None:
        try:
            zip_size = Path(self.zip_path).stat().st_size // (1024 * 1024)
            self.progress.emit(5, f"Preparing sideload ({zip_size} MB)…")
            self.log_line.emit(
                "⚠ Make sure device is in Recovery → Apply update → Apply from ADB"
            )
            self.log_line.emit(f"File: {self.zip_path}")

            cmd = [self.adb_path, "-s", self.serial, "sideload", self.zip_path]
            self.log_line.emit(f"Command: {' '.join(cmd)}")
            self.progress.emit(10, "Sending file to device…")

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                ),
            )

            for line in proc.stdout:
                line = line.strip()
                if line:
                    self.log_line.emit(line)
                    # Parse progress from adb output
                    if "%" in line:
                        import re
                        match = re.search(r"(\d+)%", line)
                        if match:
                            pct = min(int(match.group(1)), 99)
                            self.progress.emit(pct, f"Sideloading… {pct}%")

            proc.wait(timeout=600)

            if proc.returncode == 0:
                self.progress.emit(100, "Sideload complete!")
                self.finished.emit(True, "Sideload completed successfully")
            else:
                self.finished.emit(False, f"Sideload failed (code {proc.returncode})")

        except subprocess.TimeoutExpired:
            self.finished.emit(False, "Sideload timed out (10 min limit)")
        except Exception as exc:
            log.exception("Sideload error: %s", exc)
            self.finished.emit(False, str(exc))


class SideloadManager:
    """Manages OTA sideload operations."""

    def __init__(self, adb_path: str) -> None:
        self.adb_path = adb_path

    def verify_zip(self, zip_path: str) -> tuple[bool, str]:
        """Basic verification that file exists and is a zip."""
        p = Path(zip_path)
        if not p.exists():
            return False, "File not found"
        if p.suffix.lower() not in (".zip",):
            return False, "File must be a .zip package"
        if p.stat().st_size < 1024:
            return False, "File too small — may be corrupted"
        # Check ZIP magic bytes
        with open(p, "rb") as f:
            magic = f.read(4)
        if magic[:2] != b"PK":
            return False, "Not a valid ZIP file"
        return True, f"Valid ZIP ({p.stat().st_size // 1024 // 1024} MB)"

    def start_sideload(
        self,
        serial: str,
        zip_path: str,
        on_progress=None,
        on_done=None,
        on_log=None,
    ) -> SideloadWorker:
        worker = SideloadWorker(self.adb_path, serial, zip_path)
        if on_progress: worker.progress.connect(on_progress)
        if on_done:     worker.finished.connect(on_done)
        if on_log:      worker.log_line.connect(on_log)
        worker.start()
        return worker
