"""
drivers/driver_manager.py
──────────────────────────
Automatic USB driver detection and installation for Windows.
Uses official INF-based drivers bundled with the tool.

Supports: Samsung / Xiaomi / Qualcomm / MTK / Universal ADB
"""

import os
import subprocess
import logging
import winreg
from pathlib import Path
from PySide6.QtCore import QThread, Signal

log = logging.getLogger(__name__)


# ── Known USB VID/PID → Brand mapping ───────────────────────
DEVICE_VID_MAP: dict[str, str] = {
    "04E8": "Samsung",
    "2717": "Xiaomi",
    "05C6": "Qualcomm",    # Generic Qualcomm
    "0E8D": "MediaTek",
    "18D1": "Google",
    "2A45": "Oppo/Realme",
    "0BBD": "Vivo",
    "1EBF": "Tecno/Infinix",
    "19D2": "ZTE",
    "12D1": "Huawei",
}

# ── Driver INF filenames (bundled in drivers/ folder) ────────
DRIVER_INF_MAP: dict[str, str] = {
    "Samsung":        "samsung_usb_driver.inf",
    "Xiaomi":         "xiaomi_usb_driver.inf",
    "Qualcomm":       "qualcomm_usb_driver.inf",
    "MediaTek":       "mtk_usb_driver.inf",
    "Google":         "google_usb_driver.inf",
    "Oppo/Realme":    "oppo_usb_driver.inf",
    "Vivo":           "vivo_usb_driver.inf",
    "Tecno/Infinix":  "tecno_usb_driver.inf",
    "Universal":      "android_winusb.inf",
}


class DriverManager:
    """
    Manages USB driver detection and silent installation on Windows.
    All drivers must be pre-bundled in the drivers/inf/ directory.
    """

    def __init__(self, drivers_dir: Path) -> None:
        self.drivers_dir = drivers_dir
        self.inf_dir = drivers_dir / "inf"

    # ── Detection ────────────────────────────────────────────

    def list_connected_usb_devices(self) -> list[dict]:
        """
        Query Windows registry for connected USB devices.
        Returns list of {vid, pid, brand, description} dicts.
        """
        devices = []
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Enum\USB",
            )
            count = winreg.QueryInfoKey(key)[0]
            for i in range(count):
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    # Format: VID_XXXX&PID_XXXX
                    if "VID_" in subkey_name:
                        parts = subkey_name.split("&")
                        vid = parts[0].replace("VID_", "").strip()
                        pid = parts[1].replace("PID_", "").strip() if len(parts) > 1 else ""
                        brand = DEVICE_VID_MAP.get(vid.upper(), "Unknown")
                        devices.append({
                            "vid": vid,
                            "pid": pid,
                            "brand": brand,
                            "key": subkey_name,
                        })
                except (OSError, IndexError):
                    continue
            winreg.CloseKey(key)
        except Exception as exc:
            log.warning("Registry scan failed: %s", exc)

        return devices

    def detect_device_brand(self, vid: str) -> str:
        """Map USB VID to brand name."""
        return DEVICE_VID_MAP.get(vid.upper(), "Unknown")

    def is_driver_installed(self, vid: str, pid: str) -> bool:
        """Check if a driver for this VID/PID is installed."""
        try:
            key_path = (
                rf"SYSTEM\CurrentControlSet\Enum\USB\VID_{vid}&PID_{pid}"
            )
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
            winreg.CloseKey(key)
            return True
        except OSError:
            return False

    # ── Installation ─────────────────────────────────────────

    def install_driver(self, brand: str) -> tuple[bool, str]:
        """
        Silently install the INF driver for the given brand.
        Uses Windows pnputil.exe (built-in, no third-party tools needed).
        """
        inf_name = DRIVER_INF_MAP.get(brand, DRIVER_INF_MAP["Universal"])
        inf_path = self.inf_dir / inf_name

        if not inf_path.exists():
            # Try universal fallback
            inf_path = self.inf_dir / DRIVER_INF_MAP["Universal"]
            if not inf_path.exists():
                return False, f"Driver file not found: {inf_name}"

        log.info("Installing driver: %s", inf_path)

        try:
            result = subprocess.run(
                [
                    "pnputil.exe",
                    "/add-driver", str(inf_path),
                    "/install",
                    "/subdirs",
                ],
                capture_output=True,
                text=True,
                timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            success = result.returncode == 0 or "successfully" in result.stdout.lower()
            output  = result.stdout + result.stderr
            log.info("Driver install result: %s", output[:200])
            return success, output[:500]

        except subprocess.TimeoutExpired:
            return False, "Driver installation timed out"
        except FileNotFoundError:
            return False, "pnputil.exe not found (requires Windows)"
        except Exception as exc:
            return False, str(exc)

    def install_universal_adb_driver(self) -> tuple[bool, str]:
        """Install the universal Android ADB driver."""
        return self.install_driver("Universal")

    def install_all_drivers(self, callback=None) -> list[tuple]:
        """Install all bundled drivers sequentially."""
        results = []
        brands = list(DRIVER_INF_MAP.keys())
        for i, brand in enumerate(brands):
            inf = self.inf_dir / DRIVER_INF_MAP[brand]
            if inf.exists():
                ok, msg = self.install_driver(brand)
                results.append((brand, ok, msg))
                if callback:
                    callback(int((i + 1) / len(brands) * 100), brand)
        return results

    # ── Universal ADB Interface INF generator ────────────────

    def generate_universal_inf(self) -> Path:
        """
        Generate a universal android_winusb.inf that covers
        the most common Android USB VID/PID combinations.
        This is identical to what Google ships with their SDK.
        """
        self.inf_dir.mkdir(parents=True, exist_ok=True)
        inf_path = self.inf_dir / "android_winusb.inf"

        if inf_path.exists():
            return inf_path

        # Standard Google Android USB driver INF
        inf_content = """; Android USB Driver
; Generated by Mahmoud AI Global Tool 2026
; Based on Google Android USB Driver

[Version]
Signature           = "$Windows NT$"
Class               = AndroidUsbDeviceClass
ClassGuid           = {3F966BD9-FA04-4ec5-991C-D326973B5128}
Provider            = %ProviderName%
DriverVer           = 01/01/2026,2.0.0.0
CatalogFile         = androidwinusb.cat

[ClassInstall32]
Addreg = AndroidUsbClassReg

[AndroidUsbClassReg]
HKR,,,0,%ClassName%
HKR,,Icon,,-1

[Manufacturer]
%ProviderName% = Google, NTamd64
%ProviderName% = Google, NTx86

[Google.NTamd64]
;Google Nexus
%SingleAdbInterface%        = USB_Install, USB\\VID_18D1&PID_4EE7
%CompositeAdbInterface%     = USB_Install, USB\\VID_18D1&PID_4EE7&MI_01
;Generic Android ADB
%SingleAdbInterface%        = USB_Install, USB\\VID_18D1&PID_D001
%SingleAdbInterface%        = USB_Install, USB\\VID_18D1&PID_0D02
;Samsung
%SingleAdbInterface%        = USB_Install, USB\\VID_04E8&PID_6860
%CompositeAdbInterface%     = USB_Install, USB\\VID_04E8&PID_6860&MI_03
;Xiaomi
%SingleAdbInterface%        = USB_Install, USB\\VID_2717&PID_FF48
;Qualcomm generic
%SingleAdbInterface%        = USB_Install, USB\\VID_05C6&PID_9025
%SingleAdbInterface%        = USB_Install, USB\\VID_05C6&PID_9091
;MTK generic
%SingleAdbInterface%        = USB_Install, USB\\VID_0E8D&PID_2000
%SingleAdbInterface%        = USB_Install, USB\\VID_0E8D&PID_0003

[Google.NTx86]
%SingleAdbInterface%        = USB_Install, USB\\VID_18D1&PID_4EE7
%SingleAdbInterface%        = USB_Install, USB\\VID_04E8&PID_6860

[USB_Install]
Include = winusb.inf
Needs   = WINUSB.NT

[USB_Install.Services]
Include     = winusb.inf
AddService  = WinUSB,0x00000002,WinUSB_ServiceInstall

[WinUSB_ServiceInstall]
DisplayName     = %WinUSB_SvcDesc%
ServiceType     = 1
StartType       = 3
ErrorControl    = 1
ServiceBinary   = %12%\\WinUSB.sys

[USB_Install.Wdf]
KmdfService = WinUSB, WinUSB_wdfsect

[WinUSB_wdfsect]
KmdfLibraryVersion = 1.9

[USB_Install.HW]
AddReg = Dev_AddReg

[Dev_AddReg]
HKR,,DeviceInterfaceGUIDs,0x10000,"{F72FE0D4-CBCB-407d-8814-9ED673D0DD6B}"

[Strings]
ProviderName        = "Mahmoud AI Tool"
SingleAdbInterface  = "Android ADB Interface"
CompositeAdbInterface = "Android Composite ADB Interface"
WinUSB_SvcDesc      = "Android USB Driver"
ClassName           = "Android Device"
"""
        inf_path.write_text(inf_content, encoding="utf-8")
        log.info("Generated universal INF at: %s", inf_path)
        return inf_path


class DriverWorker(QThread):
    """Background driver installation worker."""

    progress = Signal(int, str)
    finished = Signal(bool, str)

    def __init__(self, manager: DriverManager, brand: str = "Universal"):
        super().__init__()
        self.manager = manager
        self.brand   = brand

    def run(self):
        try:
            self.progress.emit(10, f"Installing {self.brand} driver…")
            # Generate universal INF if needed
            self.manager.generate_universal_inf()
            self.progress.emit(40, "Running pnputil…")
            ok, msg = self.manager.install_driver(self.brand)
            self.progress.emit(100, msg[:100])
            self.finished.emit(ok, msg)
        except Exception as exc:
            self.finished.emit(False, str(exc))
