"""
samsung/samsung_tools.py
────────────────────────
Samsung-specific ADB operations:
  - CSC management
  - Knox status
  - Debloat lists
  - OTA blocker
  - Package manager
"""

import logging
from typing import Optional
from adb.adb_manager import AdbRunner

log = logging.getLogger(__name__)


# ── Well-known Samsung bloatware ─────────────────────────────
SAMSUNG_BLOAT_PACKAGES: list[str] = [
    "com.samsung.android.app.spage",
    "com.samsung.android.bixby.agent",
    "com.samsung.android.bixby.wakeup",
    "com.samsung.android.bixbyvision.framework",
    "com.samsung.android.game.gamehome",
    "com.samsung.android.game.gos",
    "com.samsung.android.game.gametools",
    "com.samsung.android.arzone",
    "com.samsung.android.ardrawing",
    "com.samsung.android.aremoji",
    "com.samsung.android.aremoji.store",
    "com.samsung.android.app.cocktailbarservice",
    "com.samsung.android.app.galaxyfinder",
    "com.samsung.android.app.tips",
    "com.sec.android.app.shealth",
    "com.samsung.android.health.widget",
    "com.sec.android.app.music",
    "com.samsung.android.app.dofinterface",
    "com.samsung.android.app.soundpicker",
    "com.samsung.android.dialer",
    "com.samsung.android.messaging",
    "com.samsung.android.email.provider",
    "com.samsung.android.calendar",
    "com.samsung.android.memo",
    "com.samsung.android.kidsinstaller",
    "com.samsung.android.scloud",
    "com.samsung.android.mapsagent",
    "com.samsung.android.app.updatecenter",
    "com.samsung.android.smartsuggestions",
    "com.samsung.android.rubin.app",
    "com.samsung.android.app.reminder",
    "com.sec.android.app.chromecustomizations",
]

# ── CSC codes ────────────────────────────────────────────────
CSC_CODES: dict[str, str] = {
    "XFE": "Middle East (Open)",
    "AFR": "Africa",
    "KSA": "Saudi Arabia",
    "UAE": "UAE",
    "EGY": "Egypt",
    "YEM": "Yemen",
    "BTU": "UK",
    "DBT": "Germany",
    "TGY": "Turkey",
    "OXM": "China / Global Export",
    "CPW": "UK (CPW)",
    "XEU": "Europe Generic",
    "TMB": "T-Mobile USA",
    "ATT": "AT&T USA",
    "VZW": "Verizon USA",
    "SPR": "Sprint USA",
    "GLB": "Global",
    "INS": "India",
    "JIO": "India (Jio)",
}


class SamsungTools:
    """
    Samsung-specific operations built on top of AdbRunner.
    All methods are synchronous (call from a worker thread).
    """

    def __init__(self, runner: AdbRunner) -> None:
        self.runner = runner

    # ── Knox ─────────────────────────────────────────────────

    def get_knox_status(self, serial: str) -> dict:
        gp = lambda p: self.runner.getprop(serial, p)
        return {
            "warranty_bit":    gp("ro.boot.warranty_bit"),
            "knox_version":    gp("ro.knox.version"),
            "knox_state":      gp("ro.boot.knoxsupport"),
            "dm_verity":       gp("ro.boot.veritymode"),
            "secure_boot":     gp("ro.boot.secureboot"),
        }

    # ── CSC ──────────────────────────────────────────────────

    def get_csc(self, serial: str) -> str:
        return (
            self.runner.getprop(serial, "ro.csc.sales_code")
            or self.runner.getprop(serial, "ro.csc.country_code")
            or self.runner.shell(serial, "cat /efs/imei/mps_code.dat").strip()
        )

    def get_csc_description(self, csc: str) -> str:
        return CSC_CODES.get(csc.upper(), "Unknown region")

    # ── One UI version ───────────────────────────────────────

    def get_one_ui_version(self, serial: str) -> str:
        raw = self.runner.getprop(serial, "ro.build.version.oneui")
        if raw:
            try:
                n = int(raw)
                major = n // 10000
                minor = (n % 10000) // 100
                return f"{major}.{minor}"
            except ValueError:
                return raw
        return ""

    # ── Debloat ──────────────────────────────────────────────

    def check_installed_packages(
        self, serial: str, packages: list[str]
    ) -> dict[str, bool]:
        """Return {package: is_installed} mapping."""
        installed = set(self.runner.list_packages(serial))
        return {pkg: pkg in installed for pkg in packages}

    def disable_package(self, serial: str, package: str) -> tuple[bool, str]:
        """pm disable-user instead of uninstall to avoid boot-loops."""
        result = self.runner.shell(
            serial, f"pm disable-user --user 0 {package}", timeout=10
        )
        success = "disabled" in result.lower()
        return success, result

    def enable_package(self, serial: str, package: str) -> tuple[bool, str]:
        result = self.runner.shell(serial, f"pm enable {package}", timeout=10)
        success = "enabled" in result.lower()
        return success, result

    def debloat_all(self, serial: str, callback=None) -> list[tuple[str, bool, str]]:
        results = []
        for i, pkg in enumerate(SAMSUNG_BLOAT_PACKAGES):
            ok, msg = self.disable_package(serial, pkg)
            results.append((pkg, ok, msg))
            if callback:
                callback(int((i + 1) / len(SAMSUNG_BLOAT_PACKAGES) * 100), pkg)
        return results

    # ── OTA Blocker ──────────────────────────────────────────

    def block_ota(self, serial: str) -> tuple[bool, str]:
        """Rename OTA folder to prevent automatic updates."""
        cmds = [
            "pm disable-user --user 0 com.wssyncmldm",
            "pm disable-user --user 0 com.samsung.android.fota",
        ]
        output = []
        for cmd in cmds:
            res = self.runner.shell(serial, cmd, timeout=10)
            output.append(res)
        ok = all("disabled" in r.lower() for r in output)
        return ok, "\n".join(output)

    def allow_ota(self, serial: str) -> tuple[bool, str]:
        cmds = [
            "pm enable com.wssyncmldm",
            "pm enable com.samsung.android.fota",
        ]
        output = []
        for cmd in cmds:
            res = self.runner.shell(serial, cmd, timeout=10)
            output.append(res)
        ok = all("enabled" in r.lower() for r in output)
        return ok, "\n".join(output)

    # ── Download Mode info ───────────────────────────────────

    def check_download_mode_capable(self, serial: str) -> bool:
        brand = self.runner.getprop(serial, "ro.product.brand").lower()
        return brand in ("samsung",)
