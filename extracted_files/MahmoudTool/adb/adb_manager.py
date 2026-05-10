"""
adb/adb_manager.py
──────────────────
Full ADB wrapper using subprocess.
All blocking I/O runs in a QThread via AdbWorker.
"""

import subprocess
import logging
import re
import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Data class – Device Info
# ─────────────────────────────────────────────────────────────

class DeviceInfo:
    """Holds all queried device properties."""

    def __init__(self, serial: str) -> None:
        self.serial          = serial
        self.model           = ""
        self.brand           = ""
        self.manufacturer    = ""
        self.android_version = ""
        self.sdk_version     = ""
        self.one_ui_version  = ""
        self.csc             = ""
        self.imei            = ""
        self.battery_level   = ""
        self.battery_health  = ""
        self.cpu_cores       = ""
        self.total_ram       = ""
        self.avail_ram       = ""
        self.total_storage   = ""
        self.avail_storage   = ""
        self.knox_status     = ""
        self.bootloader_status = ""
        self.root_status     = ""
        self.product         = ""
        self.device_state    = ""   # device / offline / unauthorized
        self.codename        = ""
        self.abi             = ""
        self.display_size    = ""
        self.ip_address      = ""

    def to_dict(self) -> dict:
        return self.__dict__


# ─────────────────────────────────────────────────────────────
# Core ADB runner
# ─────────────────────────────────────────────────────────────

class AdbRunner:
    """
    Thin wrapper around the adb binary.
    All methods are synchronous and intended to be called
    from a worker thread.
    """

    def __init__(self, adb_path: str = "adb") -> None:
        self.adb_path = adb_path

    def _run(
        self,
        args: list[str],
        serial: Optional[str] = None,
        timeout: int = 30,
        stdin_text: Optional[str] = None,
    ) -> tuple[int, str, str]:
        """
        Execute an adb command.

        Returns (returncode, stdout, stderr).
        """
        cmd = [self.adb_path]
        if serial:
            cmd += ["-s", serial]
        cmd += args

        log.debug("ADB command: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                input=stdin_text,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW
                    if os.name == "nt"
                    else 0
                ),
            )
            if result.returncode != 0:
                log.warning("ADB stderr: %s", result.stderr.strip())
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            log.error("ADB timeout for: %s", " ".join(cmd))
            return -1, "", "Timeout"
        except FileNotFoundError:
            log.error("ADB binary not found at: %s", self.adb_path)
            return -1, "", "ADB not found"
        except Exception as exc:
            log.exception("ADB exception: %s", exc)
            return -1, "", str(exc)

    # ── Device listing ───────────────────────────────────────

    def get_devices(self) -> list[dict]:
        """Return list of {serial, state} dicts."""
        _, stdout, _ = self._run(["devices"])
        devices = []
        for line in stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2:
                devices.append({"serial": parts[0], "state": parts[1]})
        return devices

    # ── Shell helper ─────────────────────────────────────────

    def shell(self, serial: str, command: str, timeout: int = 15) -> str:
        _, stdout, _ = self._run(["shell", command], serial=serial, timeout=timeout)
        return stdout

    def getprop(self, serial: str, prop: str) -> str:
        return self.shell(serial, f"getprop {prop}").strip()

    # ── Device Info ──────────────────────────────────────────

    def get_device_info(self, serial: str) -> DeviceInfo:
        info = DeviceInfo(serial)

        def gp(prop: str) -> str:
            return self.getprop(serial, prop)

        info.model            = gp("ro.product.model")
        info.brand            = gp("ro.product.brand")
        info.manufacturer     = gp("ro.product.manufacturer")
        info.android_version  = gp("ro.build.version.release")
        info.sdk_version      = gp("ro.build.version.sdk")
        info.codename         = gp("ro.product.device")
        info.abi              = gp("ro.product.cpu.abi")
        info.product          = gp("ro.build.product")

        # One UI
        info.one_ui_version   = gp("ro.build.version.oneui") or gp("ro.miui.ui.version.name")

        # CSC (Samsung)
        info.csc = (
            gp("ro.csc.country_code")
            or gp("ro.csc.sales_code")
            or gp("persist.sys.csc.sales_code")
        )

        # Battery
        batt_raw = self.shell(serial, "dumpsys battery", timeout=10)
        info.battery_level  = self._parse_dumpsys(batt_raw, "level")
        info.battery_health = self._parse_dumpsys(batt_raw, "health")

        # RAM
        mem_raw = self.shell(serial, "cat /proc/meminfo", timeout=10)
        info.total_ram = self._parse_meminfo(mem_raw, "MemTotal")
        info.avail_ram = self._parse_meminfo(mem_raw, "MemAvailable")

        # Storage
        df_raw = self.shell(serial, "df /data", timeout=10)
        info.total_storage, info.avail_storage = self._parse_df(df_raw)

        # Knox
        info.knox_status = gp("ro.boot.warranty_bit") or gp("ro.warranty_bit") or "Unknown"

        # Bootloader
        info.bootloader_status = gp("ro.boot.flash.locked") or gp("ro.secureboot.lockstate") or "Unknown"

        # Root
        su_check = self.shell(serial, "which su", timeout=5)
        info.root_status = "Rooted" if su_check.strip() else "Not Rooted"

        # Display
        wm_raw = self.shell(serial, "wm size", timeout=5)
        match = re.search(r"(\d+x\d+)", wm_raw)
        info.display_size = match.group(1) if match else ""

        # IP
        ip_raw = self.shell(serial, "ip addr show wlan0", timeout=5)
        ip_match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", ip_raw)
        info.ip_address = ip_match.group(1) if ip_match else ""

        return info

    # ── APK Management ───────────────────────────────────────

    def install_apk(self, serial: str, apk_path: str) -> tuple[bool, str]:
        code, out, err = self._run(
            ["install", "-r", "-d", apk_path], serial=serial, timeout=120
        )
        success = code == 0 and "Success" in out
        return success, out or err

    def uninstall_apk(self, serial: str, package: str) -> tuple[bool, str]:
        code, out, err = self._run(
            ["uninstall", package], serial=serial, timeout=30
        )
        return code == 0, out or err

    def list_packages(self, serial: str, flags: str = "") -> list[str]:
        cmd = f"pm list packages {flags}"
        raw = self.shell(serial, cmd, timeout=20)
        packages = []
        for line in raw.splitlines():
            if line.startswith("package:"):
                packages.append(line.split(":", 1)[1].strip())
        return sorted(packages)

    # ── File Transfer ────────────────────────────────────────

    def pull(self, serial: str, remote: str, local: str) -> tuple[bool, str]:
        code, out, err = self._run(
            ["pull", remote, local], serial=serial, timeout=120
        )
        return code == 0, out or err

    def push(self, serial: str, local: str, remote: str) -> tuple[bool, str]:
        code, out, err = self._run(
            ["push", local, remote], serial=serial, timeout=120
        )
        return code == 0, out or err

    # ── Reboot variants ──────────────────────────────────────

    def reboot(self, serial: str, mode: str = "") -> tuple[bool, str]:
        """mode: '' | 'recovery' | 'bootloader' | 'download'"""
        args = ["reboot"] + ([mode] if mode else [])
        code, out, err = self._run(args, serial=serial, timeout=10)
        return code == 0, out or err

    # ── Wireless ADB ─────────────────────────────────────────

    def enable_tcpip(self, serial: str, port: int = 5555) -> tuple[bool, str]:
        code, out, err = self._run(["tcpip", str(port)], serial=serial)
        return code == 0, out or err

    def connect_wireless(self, ip: str, port: int = 5555) -> tuple[bool, str]:
        code, out, err = self._run(["connect", f"{ip}:{port}"])
        return code == 0, out or err

    # ── Screen ───────────────────────────────────────────────

    def screenshot(self, serial: str, save_path: str) -> tuple[bool, str]:
        remote = "/sdcard/_mahmoud_screenshot.png"
        self.shell(serial, f"screencap -p {remote}")
        ok, msg = self.pull(serial, remote, save_path)
        self.shell(serial, f"rm {remote}")
        return ok, msg

    # ── Logcat ───────────────────────────────────────────────

    def get_logcat_lines(self, serial: str, lines: int = 200) -> str:
        return self.shell(serial, f"logcat -d -t {lines}", timeout=20)

    # ── Private helpers ──────────────────────────────────────

    @staticmethod
    def _parse_dumpsys(raw: str, key: str) -> str:
        for line in raw.splitlines():
            if key in line and ":" in line:
                return line.split(":", 1)[1].strip()
        return ""

    @staticmethod
    def _parse_meminfo(raw: str, key: str) -> str:
        for line in raw.splitlines():
            if line.startswith(key):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        kb = int(parts[1])
                        return f"{kb // 1024} MB"
                    except ValueError:
                        pass
        return ""

    @staticmethod
    def _parse_df(raw: str) -> tuple[str, str]:
        lines = [l for l in raw.splitlines() if "/data" in l or "data" in l.lower()]
        if lines:
            parts = lines[0].split()
            if len(parts) >= 4:
                def fmt(val: str) -> str:
                    try:
                        kb = int(val) // 1024
                        return f"{kb} MB" if kb < 1024 else f"{kb // 1024} GB"
                    except ValueError:
                        return val
                return fmt(parts[1]), fmt(parts[3])
        return "", ""


# ─────────────────────────────────────────────────────────────
# Qt Worker (runs in a QThread so GUI never blocks)
# ─────────────────────────────────────────────────────────────

class AdbWorker(QObject):
    """Generic ADB worker for long-running tasks."""

    progress    = Signal(int, str)   # (percent, message)
    finished    = Signal(bool, str)  # (success, message)
    device_info = Signal(object)     # DeviceInfo

    def __init__(
        self,
        runner: AdbRunner,
        task: str,
        serial: str = "",
        **kwargs,
    ) -> None:
        super().__init__()
        self.runner = runner
        self.task   = task
        self.serial = serial
        self.kwargs = kwargs

    def run(self) -> None:
        try:
            if self.task == "get_info":
                info = self.runner.get_device_info(self.serial)
                self.device_info.emit(info)
                self.finished.emit(True, "Device info retrieved")

            elif self.task == "install_apk":
                self.progress.emit(10, "Installing APK…")
                ok, msg = self.runner.install_apk(self.serial, self.kwargs["apk_path"])
                self.progress.emit(100, msg)
                self.finished.emit(ok, msg)

            elif self.task == "uninstall":
                ok, msg = self.runner.uninstall_apk(self.serial, self.kwargs["package"])
                self.finished.emit(ok, msg)

            elif self.task == "pull":
                ok, msg = self.runner.pull(
                    self.serial, self.kwargs["remote"], self.kwargs["local"]
                )
                self.finished.emit(ok, msg)

            elif self.task == "push":
                ok, msg = self.runner.push(
                    self.serial, self.kwargs["local"], self.kwargs["remote"]
                )
                self.finished.emit(ok, msg)

            elif self.task == "reboot":
                ok, msg = self.runner.reboot(self.serial, self.kwargs.get("mode", ""))
                self.finished.emit(ok, msg)

            elif self.task == "screenshot":
                ok, msg = self.runner.screenshot(self.serial, self.kwargs["save_path"])
                self.finished.emit(ok, msg)

            elif self.task == "get_packages":
                pkgs = self.runner.list_packages(self.serial, self.kwargs.get("flags", ""))
                self.finished.emit(True, "\n".join(pkgs))

            else:
                self.finished.emit(False, f"Unknown task: {self.task}")

        except Exception as exc:
            log.exception("AdbWorker error: %s", exc)
            self.finished.emit(False, str(exc))


class AdbThreadManager:
    """
    Convenience class to launch ADB tasks in QThreads.

    Usage:
        mgr = AdbThreadManager(runner)
        mgr.start(serial, "install_apk", apk_path="...",
                  on_done=callback, on_progress=pb_callback)
    """

    def __init__(self, runner: AdbRunner) -> None:
        self.runner  = runner
        self._threads: list[QThread] = []

    def start(
        self,
        serial: str,
        task: str,
        on_done=None,
        on_progress=None,
        on_info=None,
        **kwargs,
    ) -> tuple[QThread, AdbWorker]:
        thread = QThread()
        worker = AdbWorker(self.runner, task, serial, **kwargs)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        if on_done:
            worker.finished.connect(on_done)
        if on_progress:
            worker.progress.connect(on_progress)
        if on_info:
            worker.device_info.connect(on_info)

        # Auto-cleanup
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._threads.append(thread)
        thread.start()
        return thread, worker
