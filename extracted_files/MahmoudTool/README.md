# Mahmoud AI Global Tool Ultimate 2026

<div align="center">

```
╔══════════════════════════════════════════════════════════╗
║    Mahmoud AI Global Tool Ultimate 2026                  ║
║    Professional Android Maintenance Tool for Windows     ║
║    Version 2.0  |  Python 3.12  |  PySide6              ║
╚══════════════════════════════════════════════════════════╝
```

![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-blue)
![Python](https://img.shields.io/badge/Python-3.12-green)
![Android](https://img.shields.io/badge/Android-9--15-brightgreen)
![License](https://img.shields.io/badge/License-Professional-gold)

</div>

---

## 📋 Overview

A professional, all-in-one Android device maintenance tool for Windows repair shops.  
Features a modern dark-mode GUI, multi-brand support, and full Arabic/RTL localization.

---

## 🖥️ System Requirements

| Requirement   | Minimum              |
|---------------|----------------------|
| OS            | Windows 10 / 11 x64  |
| Python        | 3.12+                |
| RAM           | 4 GB                 |
| Storage       | 500 MB               |
| USB           | USB 2.0 or higher    |

---

## 🚀 Quick Start

### 1. Install
```batch
installer.bat
```

### 2. Run
```batch
run.bat
```

### 3. Build EXE
```batch
build.bat
```

---

## 📁 Project Structure

```
MahmoudTool/
│
├── main.py                  ← Entry point
├── requirements.txt         ← Python dependencies
├── installer.bat            ← Automatic installer
├── run.bat                  ← Launch script
├── build.bat                ← PyInstaller build
├── config.json              ← Auto-generated config
│
├── core/
│   ├── config.py            ← JSON config manager
│   ├── database.py          ← SQLite database
│   └── logger.py            ← Logging setup
│
├── adb/
│   └── adb_manager.py       ← ADB runner + QThread workers
│
├── fastboot/
│   └── fastboot_manager.py  ← Fastboot runner + workers
│
├── samsung/
│   └── samsung_tools.py     ← Knox, CSC, debloat, OTA
│
├── xiaomi/
│   └── xiaomi_tools.py      ← MIUI, HyperOS, region
│
├── localization/
│   └── localization_tools.py ← Arabic, locale, RTL, font
│
├── network/
│   └── yemen_network.py     ← Yemen APNs, VoLTE, signal
│
├── diagnostics/
│   └── diagnostics.py       ← Battery, CPU, storage, MTK, QCom
│
├── plugins/
│   └── __init__.py          ← Plugin loader
│
├── ui/
│   ├── main_window.py       ← Main window + sidebar
│   ├── splash_screen.py     ← Animated splash
│   ├── tabs/
│   │   ├── dashboard_tab.py
│   │   ├── adb_tab.py
│   │   ├── fastboot_tab.py
│   │   ├── localization_tab.py
│   │   ├── network_tab.py
│   │   ├── samsung_tab.py
│   │   ├── xiaomi_tab.py
│   │   ├── qualcomm_tab.py   ← (also contains MtkTab)
│   │   ├── smart_tools_tab.py
│   │   ├── database_tab.py
│   │   └── settings_tab.py
│   └── widgets/
│       ├── device_card.py    ← Device info card
│       └── toast.py          ← Toast notifications
│
└── assets/
    ├── styles/
    │   └── dark_theme.qss    ← Complete dark stylesheet
    ├── fonts/                ← Arabic fonts (add here)
    └── icon.ico              ← App icon
```

---

## ✨ Features

### Dashboard
- Live device list with auto-detection
- Complete device info card (Model, Android, One UI, Knox, Root…)
- Real-time logcat viewer

### ADB Tools
- APK install / uninstall
- File push / pull
- Package manager (disable / enable / uninstall)
- Wireless ADB with TCP/IP setup
- Reboot (System / Recovery / Bootloader / Download)
- Screenshot capture
- SCRCPY launcher
- Logcat viewer

### Fastboot
- Device variable reader
- Bootloader unlock / lock
- Flash any partition (recovery / boot / vbmeta / system…)
- Reboot modes

### Localization (Arabic / Multi-language)
- Change device locale (ar-YE, ar-SA, ar-EG…)
- Samsung One UI Arabic enabler
- MIUI / HyperOS Arabic enabler
- RTL layout fix
- Carrier language restriction remover (Verizon / AT&T)
- Arabic font pusher (root)
- Hidden language activator

### Yemen Networks
- Auto-create APNs for Yemen Mobile / YOU / Sabafon / Way
- SIM & carrier detection
- VoLTE / IMS status
- Signal strength reader
- Ping / connectivity test

### Samsung Tools
- Knox status reader
- CSC code reader with region description
- One UI version reader
- Samsung debloat (30+ packages)
- OTA blocker / unlocker
- Samsung package manager

### Xiaomi Tools
- MIUI / HyperOS version detection
- Region changer
- MIUI debloat (30+ packages)
- HyperOS extra cleanup
- Recovery tools

### Qualcomm Tools
- Qualcomm platform detection
- DIAG port checker
- CPU information reader
- Live CPU stats

### MediaTek Tools
- MTK platform detection
- Preloader / USB port scanner
- MTK diagnostics log

### Smart Tools
- ADB device backup
- System cache cleaner
- Battery full analysis
- Live performance monitor (RAM)
- Storage partition analyser

### Database
- Stored device history
- Operation log with status
- CSV export for devices and operations

### Settings
- Language selection
- ADB / Fastboot / SCRCPY path configuration
- Auto-detect toggle
- Notification toggle
- Update channel

---

## 🔌 Plugin System

Drop any `.py` file into the `plugins/` folder:

```python
# plugins/my_tool.py
PLUGIN_NAME    = "My Custom Tool"
PLUGIN_VERSION = "1.0"

def create_tab(runner, get_serial):
    from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
    w = QWidget()
    QVBoxLayout(w).addWidget(QLabel("My Plugin Tab"))
    return w
```

---

## 🔨 Build EXE (PyInstaller)

```batch
build.bat
```

Produces `dist\MahmoudAITool.exe` — a single-file, windowed executable.

Manual command:

```bash
pyinstaller ^
  --name="MahmoudAITool" ^
  --onefile ^
  --windowed ^
  --icon="assets\icon.ico" ^
  --add-data="assets;assets" ^
  --add-binary="tools\adb.exe;tools" ^
  --add-binary="tools\fastboot.exe;tools" ^
  main.py
```

---

## 📱 Supported Devices

| Brand    | Support Level |
|----------|--------------|
| Samsung  | Full (Knox, CSC, One UI 1–7, Download Mode) |
| Xiaomi   | Full (MIUI, HyperOS, Region) |
| Oppo / Realme | ADB / Fastboot |
| Vivo     | ADB / Fastboot |
| Google   | ADB / Fastboot |
| OnePlus  | ADB / Fastboot |
| Any Android | ADB basic |

---

## 🌐 Supported Android Versions

Android 9 (Pie) → Android 15 (V)  
One UI 1 → One UI 7  
MIUI 12 → MIUI 14  
HyperOS 1 / 2

---

## 📞 Support

**Mahmoud AI Global Tool**  
Professional Edition — 2026  
For repair shops and advanced Android users.

---

*Built with Python 3.12 + PySide6 + SQLite*
