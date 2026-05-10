"""
ui/tabs/assistant_tab.py
─────────────────────────
Smart maintenance assistant - guides technicians through
common repair procedures with step-by-step instructions.
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem,
    QPlainTextEdit, QGroupBox, QScrollArea,
    QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

log = logging.getLogger(__name__)

# ── Knowledge base of common repair procedures ───────────────
REPAIR_GUIDES: list[dict] = [
    {
        "title": "تفعيل USB Debugging",
        "category": "ADB Setup",
        "icon": "🔧",
        "steps": [
            "1. افتح الإعدادات (Settings)",
            "2. اذهب إلى 'حول الهاتف' (About Phone)",
            "3. اضغط على 'رقم البناء' (Build Number) 7 مرات متتالية",
            "4. ستظهر رسالة: 'أنت الآن مطور' (You are now a developer)",
            "5. ارجع للإعدادات → خيارات المطور (Developer Options)",
            "6. فعّل 'تصحيح USB' (USB Debugging)",
            "7. وصّل الهاتف بالكمبيوتر",
            "8. اقبل مفتاح RSA على شاشة الهاتف",
        ],
        "notes": "تنطبق على Android 4.2 وما فوق. Samsung: الإعدادات → إدارة الهاتف العام → معلومات البرنامج → رقم بناء البرنامج",
    },
    {
        "title": "الدخول لوضع Recovery",
        "category": "Boot Modes",
        "icon": "🔄",
        "steps": [
            "Samsung:",
            "  • أوقف تشغيل الهاتف تماماً",
            "  • اضغط: Vol Up + Power (أو Bixby + Vol Up + Power للأجهزة القديمة)",
            "  • اتركها عند ظهور شعار Samsung",
            "",
            "Xiaomi:",
            "  • أوقف تشغيل الهاتف",
            "  • اضغط: Vol Up + Power معاً",
            "  • اتركها عند ظهور شعار Mi",
            "",
            "عبر ADB (عند تفعيل USB Debugging):",
            "  • استخدم زر 'Reboot Recovery' في تبويب ADB",
        ],
        "notes": "تأكد من شحن البطارية أكثر من 20% قبل الدخول لأي وضع خاص",
    },
    {
        "title": "الدخول لوضع Fastboot / Bootloader",
        "category": "Boot Modes",
        "icon": "⚡",
        "steps": [
            "Samsung (Download Mode):",
            "  • أوقف التشغيل",
            "  • اضغط: Vol Down + Power",
            "  • عند ظهور التحذير اضغط Vol Up للتأكيد",
            "",
            "Xiaomi (Fastboot):",
            "  • أوقف التشغيل",
            "  • اضغط: Vol Down + Power معاً",
            "",
            "Google Pixel / Android Generic:",
            "  • أوقف التشغيل",
            "  • اضغط: Vol Down + Power",
            "",
            "عبر ADB:",
            "  • استخدم زر 'Reboot Bootloader' في تبويب ADB",
        ],
        "notes": "وضع Fastboot يستخدم للتفليش الرسمي للروم والريكفري",
    },
    {
        "title": "تثبيت تعريفات USB",
        "category": "Drivers",
        "icon": "💻",
        "steps": [
            "طريقة تلقائية (موصى بها):",
            "  1. اذهب لتبويب 'الأدوات الذكية'",
            "  2. اضغط 'تثبيت التعريفات التلقائية'",
            "  3. انتظر اكتمال التثبيت",
            "",
            "طريقة يدوية إذا فشل التلقائي:",
            "  1. افتح Device Manager على Windows",
            "  2. ابحث عن الجهاز بعلامة تحذير صفراء",
            "  3. كليك يمين → Update Driver",
            "  4. Browse my computer → اختر مجلد drivers/inf",
            "  5. ثبّت التعريف",
        ],
        "notes": "Samsung: تعريف Samsung USB Driver | Xiaomi: Xiaomi USB Driver | باقي الأجهزة: Google USB Driver",
    },
    {
        "title": "تعريب الهاتف (Samsung)",
        "category": "Localization",
        "icon": "🌐",
        "steps": [
            "عبر الأداة (موصى به):",
            "  1. وصّل الجهاز وتأكد من ظهوره في Dashboard",
            "  2. اذهب لتبويب 'التعريب'",
            "  3. اختر اللغة: العربية (ar-YE أو ar-SA)",
            "  4. فعّل 'Samsung Arabic Enable'",
            "  5. اضغط 'Run Arabization'",
            "  6. أعد تشغيل الجهاز",
            "",
            "ملاحظات One UI 7:",
            "  • يدعم العربية بشكل كامل من الإعدادات",
            "  • تأكد من تحديث One UI لآخر إصدار",
        ],
        "notes": "أجهزة Verizon/AT&T قد تحتاج 'Unlock Carrier Restriction' أولاً",
    },
    {
        "title": "إعداد شبكات اليمن (APN)",
        "category": "Network",
        "icon": "📡",
        "steps": [
            "عبر الأداة التلقائية:",
            "  1. اذهب لتبويب 'شبكات اليمن'",
            "  2. اضغط 'Create ALL Yemen APNs'",
            "  3. اختر الشريحة الصحيحة إذا طُلب",
            "  4. أعد تشغيل الهاتف",
            "",
            "يدوياً (إذا لم تعمل التلقائية):",
            "Yemen Mobile: APN=yemenmobile, MCC=421, MNC=01",
            "YOU:          APN=you,          MCC=421, MNC=02",
            "Sabafon:      APN=sabafon,       MCC=421, MNC=03",
            "Way:          APN=way,           MCC=421, MNC=04",
        ],
        "notes": "النوع: default,mms,supl,ia | البروتوكول: IPv4v6",
    },
    {
        "title": "إصلاح VoLTE",
        "category": "Network",
        "icon": "📞",
        "steps": [
            "1. اذهب لتبويب 'شبكات اليمن'",
            "2. اضغط 'VoLTE / IMS Check' للتشخيص",
            "3. إذا كان معطلاً:",
            "   • اضغط 'Enable VoLTE'",
            "   • لـ Samsung: اضغط 'Samsung VoLTE Fix'",
            "   • لـ Xiaomi:  اضغط 'Xiaomi VoLTE Fix'",
            "4. بعد التطبيق أعد تشغيل الهاتف",
            "5. تحقق مرة أخرى بـ 'VoLTE / IMS Check'",
            "",
            "إذا لم يعمل VoLTE بعد الإصلاح:",
            "  • تأكد أن الشبكة تدعم VoLTE (تواصل مع مزود الخدمة)",
            "  • جرب 'Reset IMS Config' ثم أعد المحاولة",
        ],
        "notes": "VoLTE يتطلب دعم الشبكة + دعم الجهاز + إعدادات صحيحة",
    },
    {
        "title": "نسخ احتياطي للبيانات",
        "category": "Backup",
        "icon": "💾",
        "steps": [
            "نسخ ADB الكامل:",
            "  1. اذهب لتبويب 'الأدوات الذكية'",
            "  2. اختر مكان الحفظ",
            "  3. اضغط 'ADB Backup'",
            "  4. اقبل على شاشة الهاتف",
            "  5. انتظر الاكتمال",
            "",
            "سحب الملفات الشخصية (Pull Backup):",
            "  • الصور / مقاطع الفيديو",
            "  • الواتساب / تيليغرام",
            "  • التنزيلات والمستندات",
        ],
        "notes": "Android 12+ قد يقيد ADB Backup. استخدم Pull للملفات الشخصية",
    },
    {
        "title": "تشخيص البطارية",
        "category": "Diagnostics",
        "icon": "🔋",
        "steps": [
            "1. اذهب لتبويب 'الأدوات الذكية'",
            "2. اضغط 'Analyse Battery'",
            "3. راجع النتائج:",
            "   • Level: نسبة الشحن الحالية",
            "   • Health: 2=GOOD, 3=OVERHEAT, 4=DEAD, 7=COLD",
            "   • Temperature: يجب أن تكون 20-40°C",
            "   • Voltage: طبيعي 3700-4200mV",
            "   • Cycle Count: عدد دورات الشحن",
            "",
            "تفسير نتائج الصحة (Health):",
            "  2 = جيدة ✓",
            "  3 = ساخنة - فحص الشاحن والبطارية",
            "  4 = ميتة - يلزم تبديل البطارية",
            "  7 = باردة جداً",
        ],
        "notes": "دورات الشحن فوق 500 تعني تدهور ملحوظ في سعة البطارية",
    },
    {
        "title": "تنظيف ذاكرة التخزين",
        "category": "Maintenance",
        "icon": "🗑",
        "steps": [
            "1. اذهب لتبويب 'الأدوات الذكية'",
            "2. اضغط 'Clear System Cache'",
            "   ملاحظة: يحتاج صلاحيات Root للنظام",
            "",
            "بدون Root (التطبيقات فقط):",
            "  1. اذهب لتبويب ADB → Packages",
            "  2. اختر التطبيق المراد تنظيفه",
            "  3. استخدم pm clear [package.name]",
            "",
            "تنظيف آمن من إعدادات الهاتف:",
            "  إعدادات → التخزين → بيانات مخزنة مؤقتاً",
        ],
        "notes": "لا تمسح بيانات التطبيقات المهمة (واتساب، جهات الاتصال) إلا بعد النسخ الاحتياطي",
    },
]


class GuideCard(QFrame):
    """Card displaying a single repair guide."""

    def __init__(self, guide: dict, parent=None):
        super().__init__(parent)
        self.guide = guide
        self.setObjectName("card")
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Title row
        title_row = QHBoxLayout()
        icon_lbl = QLabel(self.guide["icon"])
        icon_lbl.setFont(QFont("Segoe UI", 18))
        title_lbl = QLabel(self.guide["title"])
        title_lbl.setObjectName("sectionTitle")
        cat_lbl = QLabel(self.guide["category"])
        cat_lbl.setStyleSheet(
            "color: #1F6FEB; background: #1F6FEB22; "
            "border-radius:8px; padding:2px 8px; font-size:11px;"
        )
        title_row.addWidget(icon_lbl)
        title_row.addWidget(title_lbl, 1)
        title_row.addWidget(cat_lbl)
        layout.addLayout(title_row)

        # Steps
        for step in self.guide["steps"]:
            lbl = QLabel(step)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #E2E8F0; font-size: 12px; padding-left: 8px;")
            layout.addWidget(lbl)

        # Notes
        if self.guide.get("notes"):
            note_lbl = QLabel(f"💡 {self.guide['notes']}")
            note_lbl.setWordWrap(True)
            note_lbl.setStyleSheet(
                "color: #E3B341; font-size: 11px; "
                "background: #BB800922; border-radius:6px; padding:6px;"
            )
            layout.addWidget(note_lbl)


class AssistantTab(QWidget):
    """Smart maintenance assistant with searchable guide library."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        # Title
        title = QLabel("🧠  المساعد الذكي  •  Smart Assistant")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        subtitle = QLabel(
            "دليل شامل لخطوات الصيانة الاحترافية — اختر الإجراء من القائمة"
        )
        subtitle.setObjectName("infoKey")
        root.addWidget(subtitle)

        # Main layout: list + detail
        main = QHBoxLayout()
        root.addLayout(main, 1)

        # ── Category list ──────────────────────────────────────
        left = QWidget()
        left.setFixedWidth(240)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)

        lbl_cat = QLabel("الإجراءات المتاحة")
        lbl_cat.setObjectName("sectionTitle")
        lv.addWidget(lbl_cat)

        self.guide_list = QListWidget()
        for guide in REPAIR_GUIDES:
            item = QListWidgetItem(f"{guide['icon']}  {guide['title']}")
            item.setData(Qt.UserRole, guide)
            self.guide_list.addItem(item)
        self.guide_list.currentItemChanged.connect(self._on_guide_selected)
        lv.addWidget(self.guide_list, 1)
        main.addWidget(left)

        # ── Guide detail ──────────────────────────────────────
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self.detail_widget = QWidget()
        self.detail_layout = QVBoxLayout(self.detail_widget)
        self.detail_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.detail_widget)
        rv.addWidget(scroll, 1)

        # Quick notes area
        self.quick_notes = QPlainTextEdit()
        self.quick_notes.setPlaceholderText(
            "ملاحظاتك الخاصة عن هذه الصيانة (تحفظ محلياً)…"
        )
        self.quick_notes.setMaximumHeight(80)
        self.quick_notes.setObjectName("logViewer")
        rv.addWidget(self.quick_notes)

        main.addWidget(right, 1)

        # Select first guide
        if self.guide_list.count():
            self.guide_list.setCurrentRow(0)

    def _on_guide_selected(self, current, previous) -> None:
        if not current:
            return

        # Clear detail
        while self.detail_layout.count():
            item = self.detail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        guide = current.data(Qt.UserRole)
        if guide:
            card = GuideCard(guide)
            self.detail_layout.addWidget(card)
            self.detail_layout.addStretch()
