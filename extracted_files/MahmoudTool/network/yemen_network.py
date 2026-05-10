"""
network/yemen_network.py
────────────────────────
Yemen carrier APN management + network diagnostics.
"""

import logging
from dataclasses import dataclass
from adb.adb_manager import AdbRunner

log = logging.getLogger(__name__)


@dataclass
class ApnProfile:
    name:     str
    apn:      str
    mcc:      str
    mnc:      str
    type:     str
    protocol: str = "IPv4v6"
    mmsc:     str = ""
    mmsproxy: str = ""
    mmsport:  str = ""


YEMEN_APNS: list[ApnProfile] = [
    ApnProfile(
        name="Yemen Mobile Internet",
        apn="yemenmobile",
        mcc="421", mnc="01",
        type="default,mms,supl,ia",
    ),
    ApnProfile(
        name="YOU Internet",
        apn="you",
        mcc="421", mnc="02",
        type="default,mms,supl,ia",
    ),
    ApnProfile(
        name="Sabafon Internet",
        apn="sabafon",
        mcc="421", mnc="03",
        type="default,mms,supl,ia",
    ),
    ApnProfile(
        name="Way Internet",
        apn="way",
        mcc="421", mnc="04",
        type="default,mms,supl,ia",
    ),
    # MMS profiles
    ApnProfile(
        name="Yemen Mobile MMS",
        apn="yemenmobilemms",
        mcc="421", mnc="01",
        type="mms",
        mmsc="http://mmsc.yemenmobile/",
        mmsproxy="192.168.100.50",
        mmsport="8080",
    ),
]


class YemenNetworkTools:
    """ADB-based network configuration for Yemeni carriers."""

    def __init__(self, runner: AdbRunner) -> None:
        self.runner = runner

    # ── SIM info ─────────────────────────────────────────────

    def get_sim_info(self, serial: str) -> dict:
        raw = self.runner.shell(serial, "dumpsys telephony.registry", timeout=15)
        info: dict = {
            "mcc":        self._extract(raw, "mMcc"),
            "mnc":        self._extract(raw, "mMnc"),
            "operator":   self._extract(raw, "mOperatorName"),
            "sim_state":  self._extract(raw, "mSimState"),
            "data_state": self._extract(raw, "mDataConnectionState"),
        }
        # Detect Yemen carrier
        carrier_map = {
            ("421", "01"): "Yemen Mobile",
            ("421", "02"): "YOU",
            ("421", "03"): "Sabafon",
            ("421", "04"): "Way",
        }
        info["carrier"] = carrier_map.get(
            (info["mcc"], info["mnc"]), "Unknown"
        )
        return info

    def detect_volte_support(self, serial: str) -> dict:
        raw = self.runner.shell(serial, "dumpsys telephony.registry", timeout=15)
        ims_raw = self.runner.shell(serial, "dumpsys ims", timeout=15)
        return {
            "volte_enabled": "VoLTE" in raw or "volte" in ims_raw.lower(),
            "ims_registered": "isImsRegistered=true" in ims_raw,
            "wifi_calling":   "WiFi" in raw,
        }

    def read_signal_strength(self, serial: str) -> dict:
        raw = self.runner.shell(serial, "dumpsys telephony.registry | grep -i signal", timeout=10)
        return {"raw": raw.strip()}

    # ── APN provisioning ─────────────────────────────────────

    def create_apn_via_shell(self, serial: str, apn: ApnProfile) -> tuple[bool, str]:
        """
        Insert APN using content provider (Android 9+).
        Requires WRITE_APN_SETTINGS permission or root.
        """
        cmd = (
            f'content insert --uri content://telephony/carriers '
            f'--bind name:s:"{apn.name}" '
            f'--bind apn:s:"{apn.apn}" '
            f'--bind mcc:s:"{apn.mcc}" '
            f'--bind mnc:s:"{apn.mnc}" '
            f'--bind type:s:"{apn.type}" '
            f'--bind protocol:s:"{apn.protocol}" '
            f'--bind edited:i:1'
        )
        result = self.runner.shell(serial, cmd, timeout=10)
        ok = "Error" not in result and "Exception" not in result
        return ok, result or "APN created"

    def create_all_yemen_apns(self, serial: str, callback=None) -> list[tuple]:
        results = []
        for i, apn in enumerate(YEMEN_APNS):
            ok, msg = self.create_apn_via_shell(serial, apn)
            results.append((apn.name, ok, msg))
            if callback:
                callback(int((i + 1) / len(YEMEN_APNS) * 100), apn.name)
        return results

    # ── Network test ─────────────────────────────────────────

    def ping_test(self, serial: str, host: str = "8.8.8.8") -> dict:
        raw = self.runner.shell(
            serial, f"ping -c 4 -W 2 {host}", timeout=20
        )
        success = "4 received" in raw or "bytes from" in raw
        # Parse avg latency
        import re
        match = re.search(r"avg.*?(\d+\.\d+)", raw)
        avg_ms = match.group(1) if match else "N/A"
        return {"success": success, "output": raw, "avg_ms": avg_ms}

    # ── Helpers ──────────────────────────────────────────────

    @staticmethod
    def _extract(text: str, key: str) -> str:
        import re
        pattern = rf"{re.escape(key)}[=:\s]+([^\s,\n]+)"
        match = re.search(pattern, text)
        return match.group(1) if match else ""
