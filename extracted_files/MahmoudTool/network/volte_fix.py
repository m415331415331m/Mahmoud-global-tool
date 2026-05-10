"""
network/volte_fix.py
─────────────────────
VoLTE / IMS repair via ADB shell commands.
Works on Android 9-15, Samsung One UI, Xiaomi MIUI/HyperOS.

All commands use official Android ADB shell APIs only.
"""

import logging
from adb.adb_manager import AdbRunner

log = logging.getLogger(__name__)


class VoLTEFixer:
    """
    Repair VoLTE and IMS configurations via ADB.

    Supported operations:
    - Read IMS registration status
    - Enable VoLTE via carrier settings
    - Reset IMS configuration
    - Fix VoLTE for Yemen carriers
    - Enable VoWiFi (Wi-Fi Calling)
    """

    def __init__(self, runner: AdbRunner) -> None:
        self.runner = runner

    # ── Status Reading ───────────────────────────────────────

    def get_ims_status(self, serial: str) -> dict:
        """Read full IMS / VoLTE status."""
        raw = self.runner.shell(serial, "dumpsys telephony.registry", timeout=15)
        ims_raw = self.runner.shell(serial, "dumpsys ims", timeout=15)

        status = {
            "volte_enabled":    self._find(raw, "VoLTE") or self._find(ims_raw, "volte"),
            "ims_registered":   "isImsRegistered=true" in ims_raw,
            "ims_state":        self._extract(ims_raw, "imsServiceState"),
            "wifi_calling":     "WIFI" in ims_raw.upper(),
            "data_enabled":     self._extract(raw, "mDataEnabled"),
            "network_type":     self._extract(raw, "mNetworkType"),
            "lte_enabled":      "LTE" in raw.upper(),
        }

        # Samsung specific
        samsung_raw = self.runner.shell(
            serial, "getprop | grep volte", timeout=8
        )
        status["samsung_volte_props"] = samsung_raw.strip()

        return status

    def get_carrier_config(self, serial: str) -> str:
        """Dump carrier configuration (includes VoLTE settings)."""
        return self.runner.shell(
            serial, "dumpsys carrier_config", timeout=15
        )

    # ── VoLTE Enable ─────────────────────────────────────────

    def enable_volte(self, serial: str) -> tuple[bool, str]:
        """
        Enable VoLTE via ADB settings commands.
        Works on most Android devices.
        """
        commands = [
            # Global VoLTE switch
            "settings put global volte_vt_enabled 1",
            "settings put global enhanced_4g_mode_enabled 1",
            # IMS settings
            "settings put secure enhanced_4g_mode_enabled 1",
            "settings put secure volte_enabled 1",
            # Carrier settings
            "settings put global carrier_volte_available 1",
            "settings put global carrier_vt_available 1",
        ]
        results = []
        for cmd in commands:
            result = self.runner.shell(serial, cmd, timeout=8)
            results.append(f"✓ {cmd.split('put ')[-1]}: {result or 'OK'}")

        # Restart IMS service
        restart = self.runner.shell(
            serial,
            "am broadcast -a android.intent.action.IMS_STATE_CHANGED",
            timeout=8,
        )
        results.append(f"IMS broadcast: {restart or 'sent'}")

        return True, "\n".join(results)

    def enable_vowifi(self, serial: str) -> tuple[bool, str]:
        """Enable Wi-Fi Calling (VoWiFi)."""
        commands = [
            "settings put global wifi_calling_mode 0",
            "settings put secure wifi_calling_enabled 1",
            "settings put global carrier_wfc_ims_available 1",
        ]
        results = []
        for cmd in commands:
            r = self.runner.shell(serial, cmd, timeout=8)
            results.append(f"✓ {r or 'OK'}")
        return True, "\n".join(results)

    # ── Samsung VoLTE ────────────────────────────────────────

    def enable_samsung_volte(self, serial: str) -> tuple[bool, str]:
        """
        Samsung-specific VoLTE enablement.
        Uses Samsung telephony properties.
        """
        commands = [
            "setprop persist.dbg.volte_avail_ovr 1",
            "setprop persist.dbg.wfc_avail_ovr 1",
            "setprop persist.dbg.vt_avail_ovr 1",
            "settings put global volte_vt_enabled 1",
            "settings put global enhanced_4g_mode_enabled 1",
        ]
        results = []
        for cmd in commands:
            r = self.runner.shell(serial, cmd, timeout=8)
            results.append(f"  {cmd}: {r or 'OK'}")

        # Restart Samsung telephony
        r2 = self.runner.shell(
            serial,
            "am broadcast -a com.samsung.android.intent.action.IMS_REFRESH",
            timeout=8,
        )
        results.append(f"  Samsung IMS refresh: {r2 or 'sent'}")

        return True, "\n".join(results)

    # ── Xiaomi VoLTE ─────────────────────────────────────────

    def enable_xiaomi_volte(self, serial: str) -> tuple[bool, str]:
        """Xiaomi MIUI/HyperOS VoLTE enablement."""
        commands = [
            "setprop persist.dbg.volte_avail_ovr 1",
            "settings put global volte_vt_enabled 1",
            "settings put global enhanced_4g_mode_enabled 1",
            "settings put secure enhanced_4g_mode_enabled 1",
        ]
        results = []
        for cmd in commands:
            r = self.runner.shell(serial, cmd, timeout=8)
            results.append(f"  {cmd}: {r or 'OK'}")
        return True, "\n".join(results)

    # ── Yemen Carrier VoLTE ──────────────────────────────────

    def fix_volte_yemen_mobile(self, serial: str) -> tuple[bool, str]:
        """
        Fix VoLTE for Yemen Mobile (MCC 421, MNC 01).
        Applies carrier-specific IMS configuration.
        """
        results = []

        # Set APN with IMS type
        apn_cmd = (
            "content insert --uri content://telephony/carriers "
            "--bind name:s:\"Yemen Mobile IMS\" "
            "--bind apn:s:\"yemenmobile\" "
            "--bind mcc:s:\"421\" "
            "--bind mnc:s:\"01\" "
            "--bind type:s:\"default,mms,supl,ia,ims\" "
            "--bind protocol:s:\"IPv4v6\" "
            "--bind edited:i:1"
        )
        r1 = self.runner.shell(serial, apn_cmd, timeout=10)
        results.append(f"IMS APN: {r1 or 'created'}")

        # Enable VoLTE
        ok, msg = self.enable_volte(serial)
        results.append(msg)

        return True, "\n".join(results)

    def fix_volte_you(self, serial: str) -> tuple[bool, str]:
        """Fix VoLTE for YOU (MCC 421, MNC 02)."""
        results = []
        apn_cmd = (
            "content insert --uri content://telephony/carriers "
            "--bind name:s:\"YOU IMS\" "
            "--bind apn:s:\"you\" "
            "--bind mcc:s:\"421\" "
            "--bind mnc:s:\"02\" "
            "--bind type:s:\"default,mms,supl,ia,ims\" "
            "--bind protocol:s:\"IPv4v6\" "
            "--bind edited:i:1"
        )
        r1 = self.runner.shell(serial, apn_cmd, timeout=10)
        results.append(f"IMS APN: {r1 or 'created'}")
        ok, msg = self.enable_volte(serial)
        results.append(msg)
        return True, "\n".join(results)

    # ── IMS Reset ────────────────────────────────────────────

    def reset_ims_config(self, serial: str) -> tuple[bool, str]:
        """
        Reset IMS configuration to defaults.
        Useful when VoLTE is corrupted.
        """
        commands = [
            # Clear IMS database
            "pm clear com.android.ims",
            "pm clear com.samsung.android.ims",
            # Reset settings
            "settings delete global volte_vt_enabled",
            "settings delete global enhanced_4g_mode_enabled",
            # Re-enable
            "settings put global volte_vt_enabled 1",
            "settings put global enhanced_4g_mode_enabled 1",
        ]
        results = []
        for cmd in commands:
            r = self.runner.shell(serial, cmd, timeout=10)
            results.append(f"  {cmd.split()[-1]}: {r or 'OK'}")

        return True, "\n".join(results)

    def restart_telephony(self, serial: str) -> tuple[bool, str]:
        """Restart telephony stack to apply changes."""
        cmds = [
            "am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true",
            "sleep 2",
            "am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false",
        ]
        for cmd in cmds:
            self.runner.shell(serial, cmd, timeout=10)
        return True, "Telephony restarted (airplane mode cycle)"

    # ── Helpers ──────────────────────────────────────────────

    @staticmethod
    def _find(text: str, keyword: str) -> bool:
        return keyword.lower() in text.lower()

    @staticmethod
    def _extract(text: str, key: str) -> str:
        import re
        pattern = rf"{re.escape(key)}[=:\s]+([^\s,\n]+)"
        match = re.search(pattern, text)
        return match.group(1) if match else "Unknown"
