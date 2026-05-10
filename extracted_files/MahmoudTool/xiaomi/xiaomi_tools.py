"""
xiaomi/xiaomi_tools.py
──────────────────────
Xiaomi / MIUI / HyperOS specific operations.
"""

import logging
from adb.adb_manager import AdbRunner

log = logging.getLogger(__name__)


MIUI_BLOAT_PACKAGES: list[str] = [
    "com.miui.analytics",
    "com.miui.msa.global",
    "com.xiaomi.mipicks",
    "com.miui.bugreport",
    "com.miui.cloudservice",
    "com.miui.cloudservice.sysbase",
    "com.miui.cloudbackup",
    "com.miui.backup",
    "com.miui.newmidrive",
    "com.miui.player",
    "com.mi.health",
    "com.miui.videoplayer",
    "com.mi.globalbrowser",
    "com.miui.notes",
    "com.xiaomi.scanner",
    "com.miui.weather2",
    "com.miui.compass",
    "com.miui.calculator",
    "com.miui.yellowpage",
    "com.miui.phone",
    "com.miui.translation.youdao",
    "com.miui.translation.kingsoft",
    "com.miui.android.fashiongallery",
    "com.miui.contentcatcher",
    "com.miui.daemon",
    "com.miui.system",
    "com.miui.securityadd",
    "com.miui.virtualsim",
    "com.facebook.system",
    "com.facebook.appmanager",
    "com.facebook.services",
]

HYPEROS_BLOAT_PACKAGES: list[str] = [
    "com.xiaomi.aiasst.service",
    "com.xiaomi.xmsf",
    "com.xiaomi.joyose",
    "com.xiaomi.discover",
    "com.xiaomi.finddevice",
    "com.xiaomi.payment",
    "com.xiaomi.account",
]

XIAOMI_REGIONS: dict[str, str] = {
    "global":  "Global",
    "cn":      "China",
    "eea":     "Europe (EEA)",
    "ru":      "Russia",
    "in":      "India",
    "id":      "Indonesia",
    "tr":      "Turkey",
}


class XiaomiTools:
    def __init__(self, runner: AdbRunner) -> None:
        self.runner = runner

    # ── MIUI / HyperOS detection ─────────────────────────────

    def get_miui_version(self, serial: str) -> str:
        return self.runner.getprop(serial, "ro.miui.ui.version.name") or \
               self.runner.getprop(serial, "ro.miui.version")

    def get_hyperos_version(self, serial: str) -> str:
        return self.runner.getprop(serial, "ro.mi.os.version.name") or \
               self.runner.getprop(serial, "ro.hyperos.version")

    def is_hyperos(self, serial: str) -> bool:
        return bool(self.get_hyperos_version(serial))

    def get_region(self, serial: str) -> str:
        return (
            self.runner.getprop(serial, "ro.miui.region")
            or self.runner.getprop(serial, "ro.product.region")
        )

    # ── Debloat ──────────────────────────────────────────────

    def debloat_miui(self, serial: str, callback=None) -> list[tuple]:
        packages = MIUI_BLOAT_PACKAGES + (
            HYPEROS_BLOAT_PACKAGES if self.is_hyperos(serial) else []
        )
        results = []
        for i, pkg in enumerate(packages):
            res = self.runner.shell(
                serial, f"pm disable-user --user 0 {pkg}", timeout=10
            )
            ok = "disabled" in res.lower()
            results.append((pkg, ok, res))
            if callback:
                callback(int((i + 1) / len(packages) * 100), pkg)
        return results

    # ── Region changer ───────────────────────────────────────

    def change_region(self, serial: str, region_code: str) -> tuple[bool, str]:
        """
        Attempt to change region via persist properties.
        Note: Full region change on modern MIUI/HyperOS requires fastboot.
        """
        cmds = [
            f"setprop ro.miui.region {region_code.upper()}",
            f"setprop ro.product.region {region_code.lower()}",
        ]
        outputs = []
        for cmd in cmds:
            outputs.append(self.runner.shell(serial, cmd))
        return True, "\n".join(outputs)

    # ── Recovery tools ───────────────────────────────────────

    def enable_adb_in_recovery(self, serial: str) -> tuple[bool, str]:
        """Boot into recovery with ADB enabled (MIUI specific)."""
        ok, msg = self.runner.reboot(serial, "recovery")
        return ok, msg
