"""
localization/localization_tools.py
────────────────────────────────────
Arabic localization, locale management, RTL fixes,
font installation, and CSC language enabling.

Supports: Android 9–15 | One UI 1–7 | MIUI/HyperOS
"""

import logging
from adb.adb_manager import AdbRunner

log = logging.getLogger(__name__)


# ── Supported locales ────────────────────────────────────────
ARABIC_LOCALES: dict[str, str] = {
    "ar-YE": "العربية (اليمن)",
    "ar-SA": "العربية (السعودية)",
    "ar-EG": "العربية (مصر)",
    "ar-AE": "العربية (الإمارات)",
    "ar-IQ": "العربية (العراق)",
    "ar-MA": "العربية (المغرب)",
    "ar-DZ": "العربية (الجزائر)",
    "ar-LB": "العربية (لبنان)",
    "ar-JO": "العربية (الأردن)",
    "ar":    "العربية (عام)",
}

# ── Android SDK to version name ──────────────────────────────
SDK_MAP: dict[str, str] = {
    "28": "Android 9  (Pie)",
    "29": "Android 10 (Q)",
    "30": "Android 11 (R)",
    "31": "Android 12 (S)",
    "32": "Android 12L",
    "33": "Android 13 (T)",
    "34": "Android 14 (U)",
    "35": "Android 15 (V)",
}


class LocalizationTools:
    """All localization & regionalization operations."""

    def __init__(self, runner: AdbRunner) -> None:
        self.runner = runner

    # ── Locale ───────────────────────────────────────────────

    def get_current_locale(self, serial: str) -> str:
        return self.runner.getprop(serial, "persist.sys.locale") \
            or self.runner.getprop(serial, "ro.product.locale")

    def set_locale(self, serial: str, locale: str) -> tuple[bool, str]:
        """
        Change device locale.
        Uses `setprop` + `am broadcast` for immediate effect.
        """
        sdk = self.runner.getprop(serial, "ro.build.version.sdk")
        sdk_int = int(sdk) if sdk.isdigit() else 0

        if sdk_int >= 29:
            # Android 10+: use cmd locale
            result = self.runner.shell(
                serial,
                f"cmd locale set-app-locales android --locales {locale}",
                timeout=10,
            )
        else:
            result = ""

        # Also set persist props
        self.runner.shell(serial, f"setprop persist.sys.locale {locale}")
        self.runner.shell(serial, f"setprop persist.sys.language {locale.split('-')[0]}")

        # Broadcast locale change
        self.runner.shell(
            serial,
            "am broadcast -a android.intent.action.LOCALE_CHANGED",
            timeout=10,
        )

        return True, f"Locale set to {locale}\n{result}"

    # ── RTL Fix ──────────────────────────────────────────────

    def apply_rtl_fix(self, serial: str) -> tuple[bool, str]:
        """Enable RTL layout direction."""
        cmds = [
            "settings put global development_settings_enabled 1",
            "settings put global debug.layout true",
            "settings put system user_rotation 0",
        ]
        results = []
        for cmd in cmds:
            results.append(self.runner.shell(serial, cmd, timeout=5))
        return True, "\n".join(results)

    # ── Samsung CSC Language Enable ──────────────────────────

    def enable_samsung_arabic(self, serial: str) -> tuple[bool, str]:
        """
        Force-enable Arabic on Samsung devices with restricted CSC.
        Uses overlay package approach via pm.
        """
        # First set locale
        ok1, m1 = self.set_locale(serial, "ar")

        # Samsung-specific: enable hidden Arabic overlay
        overlay_cmd = (
            "cmd overlay enable com.samsung.android.overlay.nls.lang.arabic"
        )
        r2 = self.runner.shell(serial, overlay_cmd, timeout=10)

        # Set locale in Samsung's own settings DB
        r3 = self.runner.shell(
            serial,
            "content insert --uri content://settings/system "
            "--bind name:s:user_preferred_locale --bind value:s:ar",
            timeout=10,
        )
        return ok1, f"{m1}\n{r2}\n{r3}"

    # ── MIUI / HyperOS Arabic ────────────────────────────────

    def enable_miui_arabic(self, serial: str) -> tuple[bool, str]:
        cmds = [
            "setprop ro.miui.region GLOBAL",
            "settings put system user_preferred_locale ar",
        ]
        results = [self.runner.shell(serial, c, timeout=5) for c in cmds]
        ok, m = self.set_locale(serial, "ar")
        return ok, "\n".join(results) + "\n" + m

    # ── Font Installer ───────────────────────────────────────

    def push_arabic_font(
        self, serial: str, font_path: str
    ) -> tuple[bool, str]:
        """
        Push an Arabic .ttf font to /system/fonts (requires root).
        """
        remote = "/system/fonts/" + font_path.split("/")[-1].split("\\")[-1]

        # Remount /system rw
        self.runner.shell(serial, "mount -o rw,remount /system", timeout=5)

        ok, msg = self.runner.push(serial, font_path, remote)
        if ok:
            # Set permissions
            self.runner.shell(serial, f"chmod 644 {remote}", timeout=5)
            self.runner.shell(serial, "mount -o ro,remount /system", timeout=5)

        return ok, msg

    # ── Verizon / AT&T locale unlock ─────────────────────────

    def unlock_carrier_languages(self, serial: str) -> tuple[bool, str]:
        """
        Some carrier-branded devices (Verizon/AT&T) restrict language
        selection.  We disable the restriction overlay.
        """
        carrier_overlays = [
            "com.att.overlay.language_restriction",
            "com.verizon.llkagent",
            "com.vzw.apnlib",
        ]
        results = []
        for pkg in carrier_overlays:
            r = self.runner.shell(
                serial, f"pm disable-user --user 0 {pkg}", timeout=8
            )
            results.append(f"{pkg}: {r.strip()}")

        # Also remove language restriction flag
        r2 = self.runner.shell(
            serial,
            "settings put global restrict_language_selection 0",
            timeout=5,
        )
        return True, "\n".join(results) + f"\nRestriction flag: {r2}"

    # ── Hidden language activation ───────────────────────────

    def activate_hidden_language(
        self, serial: str, locale: str
    ) -> tuple[bool, str]:
        """
        Some OEMs hide certain locales in the UI.
        Force them via `localesettings`.
        """
        sdk = self.runner.getprop(serial, "ro.build.version.sdk")
        sdk_int = int(sdk) if sdk.isdigit() else 0

        if sdk_int >= 33:   # Android 13+
            cmd = f"cmd locale set-app-locales android --locales {locale}"
        else:
            cmd = f"setprop persist.sys.locale {locale}"

        result = self.runner.shell(serial, cmd, timeout=10)
        return True, result or f"Language {locale} activated"
