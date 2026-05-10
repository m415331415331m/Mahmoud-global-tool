"""
localization/i18n.py
─────────────────────
Simple key-based translation system.
Usage:
    from localization.i18n import t, set_language
    set_language("ar")
    print(t("dashboard"))   # → "لوحة التحكم"
"""

from __future__ import annotations

_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "dashboard":        "Dashboard",
        "adb_tools":        "ADB Tools",
        "fastboot":         "Fastboot",
        "localization":     "Localization",
        "yemen_networks":   "Yemen Networks",
        "samsung":          "Samsung",
        "xiaomi":           "Xiaomi",
        "qualcomm":         "Qualcomm",
        "mediatek":         "MediaTek",
        "smart_tools":      "Smart Tools",
        "database":         "Database",
        "settings":         "Settings",
        "no_device":        "No Device Connected",
        "connected":        "Connected",
        "disconnected":     "Disconnected",
        "refresh":          "Refresh",
        "install":          "Install",
        "uninstall":        "Uninstall",
        "push":             "Push",
        "pull":             "Pull",
        "reboot":           "Reboot",
        "save":             "Save",
        "cancel":           "Cancel",
        "browse":           "Browse",
        "export":           "Export",
        "clear":            "Clear",
        "apply":            "Apply",
    },
    "ar": {
        "dashboard":        "لوحة التحكم",
        "adb_tools":        "أدوات ADB",
        "fastboot":         "فاست بوت",
        "localization":     "التعريب",
        "yemen_networks":   "شبكات اليمن",
        "samsung":          "سامسونج",
        "xiaomi":           "شاومي",
        "qualcomm":         "كوالكوم",
        "mediatek":         "ميدياتك",
        "smart_tools":      "الأدوات الذكية",
        "database":         "قاعدة البيانات",
        "settings":         "الإعدادات",
        "no_device":        "لا يوجد جهاز متصل",
        "connected":        "متصل",
        "disconnected":     "غير متصل",
        "refresh":          "تحديث",
        "install":          "تثبيت",
        "uninstall":        "إلغاء تثبيت",
        "push":             "رفع",
        "pull":             "سحب",
        "reboot":           "إعادة تشغيل",
        "save":             "حفظ",
        "cancel":           "إلغاء",
        "browse":           "تصفح",
        "export":           "تصدير",
        "clear":            "مسح",
        "apply":            "تطبيق",
    },
}

_lang: str = "ar"


def set_language(lang: str) -> None:
    global _lang
    if lang in _TRANSLATIONS:
        _lang = lang


def t(key: str, fallback: str = "") -> str:
    lang_dict = _TRANSLATIONS.get(_lang, {})
    result = lang_dict.get(key)
    if result:
        return result
    # Fallback to English
    en_dict = _TRANSLATIONS.get("en", {})
    return en_dict.get(key, fallback or key)
