"""
diagnostics/diagnostics.py
───────────────────────────
Device diagnostics: battery, storage, performance, Qualcomm, MTK.
"""

import logging
import re
from adb.adb_manager import AdbRunner

log = logging.getLogger(__name__)


class DiagnosticsTools:
    def __init__(self, runner: AdbRunner) -> None:
        self.runner = runner

    # ── Battery Analysis ─────────────────────────────────────

    def get_battery_full(self, serial: str) -> dict:
        raw = self.runner.shell(serial, "dumpsys battery", timeout=15)
        keys = [
            "level", "scale", "status", "health",
            "voltage", "temperature", "technology",
            "AC powered", "USB powered", "Wireless powered",
        ]
        result = {}
        for key in keys:
            for line in raw.splitlines():
                if key.lower() in line.lower() and ":" in line:
                    result[key] = line.split(":", 1)[1].strip()
                    break
        # Convert temperature (tenths of a degree C)
        if "temperature" in result:
            try:
                result["temperature_c"] = str(int(result["temperature"]) / 10) + " °C"
            except ValueError:
                pass
        return result

    def get_battery_stats(self, serial: str) -> str:
        return self.runner.shell(serial, "dumpsys batterystats --charged", timeout=20)

    # ── Storage ──────────────────────────────────────────────

    def get_storage_full(self, serial: str) -> dict:
        raw = self.runner.shell(serial, "df -h", timeout=10)
        partitions = {}
        for line in raw.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 6:
                partitions[parts[5]] = {
                    "total": parts[1],
                    "used":  parts[2],
                    "avail": parts[3],
                    "use%":  parts[4],
                }
        return partitions

    # ── Performance ──────────────────────────────────────────

    def get_cpu_info(self, serial: str) -> dict:
        model  = self.runner.shell(serial, "cat /proc/cpuinfo | grep 'Hardware'", timeout=8)
        cores  = self.runner.shell(serial, "cat /proc/cpuinfo | grep -c processor", timeout=8)
        freq   = self.runner.shell(serial, "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq", timeout=5)
        maxf   = self.runner.shell(serial, "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq", timeout=5)
        top_raw = self.runner.shell(serial, "top -n 1 -b", timeout=10)
        return {
            "hardware": model.split(":")[-1].strip() if ":" in model else "Unknown",
            "cores":    cores.strip(),
            "cur_freq_mhz": str(int(freq.strip()) // 1000) if freq.strip().isdigit() else "N/A",
            "max_freq_mhz": str(int(maxf.strip()) // 1000) if maxf.strip().isdigit() else "N/A",
            "top_snapshot": top_raw[:500],
        }

    def get_ram_usage(self, serial: str) -> dict:
        raw = self.runner.shell(serial, "cat /proc/meminfo", timeout=8)
        result = {}
        for line in raw.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                nums = re.findall(r"\d+", val)
                if nums:
                    kb = int(nums[0])
                    result[key.strip()] = f"{kb // 1024} MB"
        return result

    # ── Cache Cleaner ────────────────────────────────────────

    def clear_app_cache(self, serial: str, package: str) -> tuple[bool, str]:
        result = self.runner.shell(serial, f"pm clear {package}", timeout=10)
        return "Success" in result, result

    def clear_system_cache(self, serial: str) -> tuple[bool, str]:
        """Clear dalvik-cache and package caches (may need root)."""
        cmds = [
            "rm -rf /data/dalvik-cache/*",
            "rm -rf /data/resource-cache/*",
            "sync",
        ]
        out = [self.runner.shell(serial, c, timeout=10) for c in cmds]
        return True, "\n".join(out)

    # ── Logcat ───────────────────────────────────────────────

    def get_logcat(self, serial: str, lines: int = 300) -> str:
        return self.runner.shell(serial, f"logcat -d -t {lines}", timeout=30)

    def clear_logcat(self, serial: str) -> str:
        return self.runner.shell(serial, "logcat -c", timeout=5)

    # ── Qualcomm ─────────────────────────────────────────────

    def detect_qualcomm(self, serial: str) -> dict:
        soc = self.runner.getprop(serial, "ro.board.platform")
        is_qcom = soc.lower().startswith(("sm", "sdm", "msm", "qcom", "lahaina", "taro", "kalama"))
        return {
            "platform": soc,
            "is_qualcomm": is_qcom,
            "chipset": self.runner.getprop(serial, "ro.hardware"),
        }

    def check_diag_mode(self, serial: str) -> str:
        """Check if Qualcomm diagnostic port is accessible."""
        raw = self.runner.shell(serial, "ls /dev/diag", timeout=5)
        return "Available" if "/dev/diag" in raw else "Not Available"

    # ── MediaTek ─────────────────────────────────────────────

    def detect_mtk(self, serial: str) -> dict:
        soc = self.runner.getprop(serial, "ro.board.platform")
        is_mtk = soc.lower().startswith(("mt", "helio", "dimensity"))
        return {
            "platform": soc,
            "is_mediatek": is_mtk,
            "chipset": self.runner.getprop(serial, "ro.mediatek.platform"),
        }

    def check_preloader(self, serial: str) -> str:
        raw = self.runner.shell(serial, "ls /dev/ttyS*", timeout=5)
        return raw.strip() or "No preloader ports found"

    # ── Backup / Restore ─────────────────────────────────────

    def backup_device(self, serial: str, output_path: str) -> tuple[bool, str]:
        """ADB backup (Android < 12 may require device confirmation)."""
        import subprocess, os
        cmd = [
            "adb", "-s", serial,
            "backup", "-apk", "-shared", "-all",
            "-f", output_path,
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300,
                creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as exc:
            return False, str(exc)
