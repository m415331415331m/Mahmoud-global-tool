"""
fastboot/fastboot_manager.py
────────────────────────────
Fastboot command wrapper + QThread worker.
"""

import subprocess
import logging
import os
from typing import Optional
from PySide6.QtCore import QObject, QThread, Signal

log = logging.getLogger(__name__)


class FastbootRunner:
    """Synchronous fastboot wrapper."""

    def __init__(self, fastboot_path: str = "fastboot") -> None:
        self.fastboot_path = fastboot_path

    def _run(
        self,
        args: list[str],
        serial: Optional[str] = None,
        timeout: int = 60,
    ) -> tuple[int, str, str]:
        cmd = [self.fastboot_path]
        if serial:
            cmd += ["-s", serial]
        cmd += args

        log.debug("Fastboot: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "Timeout"
        except FileNotFoundError:
            return -1, "", "Fastboot binary not found"
        except Exception as exc:
            return -1, "", str(exc)

    # ── Device discovery ─────────────────────────────────────

    def get_devices(self) -> list[dict]:
        _, out, _ = self._run(["devices"])
        devices = []
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "fastboot":
                devices.append({"serial": parts[0], "state": "fastboot"})
        return devices

    # ── Device info ──────────────────────────────────────────

    def get_var(self, serial: str, var: str) -> str:
        _, out, err = self._run(["getvar", var], serial=serial, timeout=10)
        # fastboot prints to stderr
        combined = out + err
        for line in combined.splitlines():
            if var in line:
                return line.split(":", 1)[-1].strip()
        return ""

    def get_all_vars(self, serial: str) -> dict:
        _, out, err = self._run(["getvar", "all"], serial=serial, timeout=15)
        combined = out + err
        result = {}
        for line in combined.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                result[key.strip()] = val.strip()
        return result

    # ── Bootloader ───────────────────────────────────────────

    def unlock_bootloader(self, serial: str) -> tuple[bool, str]:
        code, out, err = self._run(
            ["flashing", "unlock"], serial=serial, timeout=30
        )
        return code == 0, out or err

    def lock_bootloader(self, serial: str) -> tuple[bool, str]:
        code, out, err = self._run(
            ["flashing", "lock"], serial=serial, timeout=30
        )
        return code == 0, out or err

    # ── Flash ────────────────────────────────────────────────

    def flash(
        self, serial: str, partition: str, image_path: str
    ) -> tuple[bool, str]:
        code, out, err = self._run(
            ["flash", partition, image_path], serial=serial, timeout=300
        )
        return code == 0, out or err

    def flash_recovery(self, serial: str, img: str) -> tuple[bool, str]:
        return self.flash(serial, "recovery", img)

    def flash_boot(self, serial: str, img: str) -> tuple[bool, str]:
        return self.flash(serial, "boot", img)

    def flash_vbmeta(self, serial: str, img: str) -> tuple[bool, str]:
        # Disable verification when flashing vbmeta
        self._run(
            ["--disable-verity", "--disable-verification",
             "flash", "vbmeta", img],
            serial=serial,
            timeout=60,
        )
        return self.flash(serial, "vbmeta", img)

    # ── Reboot ───────────────────────────────────────────────

    def reboot(self, serial: str, mode: str = "") -> tuple[bool, str]:
        args = ["reboot"] + ([mode] if mode else [])
        code, out, err = self._run(args, serial=serial, timeout=15)
        return code == 0, out or err


# ─────────────────────────────────────────────────────────────
# Qt Worker
# ─────────────────────────────────────────────────────────────

class FastbootWorker(QObject):
    progress  = Signal(int, str)
    finished  = Signal(bool, str)
    vars_ready = Signal(dict)

    def __init__(
        self, runner: FastbootRunner, task: str, serial: str = "", **kwargs
    ) -> None:
        super().__init__()
        self.runner = runner
        self.task   = task
        self.serial = serial
        self.kwargs = kwargs

    def run(self) -> None:
        try:
            if self.task == "get_vars":
                self.progress.emit(30, "Reading device variables…")
                data = self.runner.get_all_vars(self.serial)
                self.vars_ready.emit(data)
                self.finished.emit(True, "Done")

            elif self.task == "unlock":
                self.progress.emit(10, "Sending unlock command…")
                ok, msg = self.runner.unlock_bootloader(self.serial)
                self.finished.emit(ok, msg)

            elif self.task == "lock":
                ok, msg = self.runner.lock_bootloader(self.serial)
                self.finished.emit(ok, msg)

            elif self.task == "flash":
                partition = self.kwargs["partition"]
                image     = self.kwargs["image"]
                self.progress.emit(10, f"Flashing {partition}…")
                ok, msg = self.runner.flash(self.serial, partition, image)
                self.progress.emit(100, msg)
                self.finished.emit(ok, msg)

            elif self.task == "reboot":
                mode = self.kwargs.get("mode", "")
                ok, msg = self.runner.reboot(self.serial, mode)
                self.finished.emit(ok, msg)

            else:
                self.finished.emit(False, f"Unknown task: {self.task}")

        except Exception as exc:
            log.exception("FastbootWorker: %s", exc)
            self.finished.emit(False, str(exc))


class FastbootThreadManager:
    def __init__(self, runner: FastbootRunner) -> None:
        self.runner  = runner
        self._threads: list[QThread] = []

    def start(
        self,
        serial: str,
        task: str,
        on_done=None,
        on_progress=None,
        on_vars=None,
        **kwargs,
    ) -> tuple[QThread, FastbootWorker]:
        thread = QThread()
        worker = FastbootWorker(self.runner, task, serial, **kwargs)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        if on_done:
            worker.finished.connect(on_done)
        if on_progress:
            worker.progress.connect(on_progress)
        if on_vars:
            worker.vars_ready.connect(on_vars)

        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._threads.append(thread)
        thread.start()
        return thread, worker
