"""
ui/widgets/device_card.py
──────────────────────────
Reusable device info card widget.
"""

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class InfoRow(QWidget):
    """A single key-value row inside a card."""

    def __init__(self, key: str, value: str = "—", parent=None):
        from PySide6.QtWidgets import QWidget
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        lbl_key = QLabel(key)
        lbl_key.setObjectName("infoKey")
        lbl_key.setFixedWidth(160)

        self.lbl_value = QLabel(value)
        self.lbl_value.setObjectName("infoValue")
        self.lbl_value.setWordWrap(True)

        layout.addWidget(lbl_key)
        layout.addWidget(self.lbl_value, 1)

    def set_value(self, v: str) -> None:
        self.lbl_value.setText(v or "—")


class DeviceCard(QFrame):
    """
    Card widget showing device status and basic info.
    Emits `refresh_requested` when the user clicks Refresh.
    """

    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statusCard")
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── Header ───────────────────────────────────────────
        header = QHBoxLayout()
        self.lbl_model = QLabel("No Device Connected")
        self.lbl_model.setObjectName("deviceModel")

        self.lbl_status = QLabel("●  Disconnected")
        self.lbl_status.setObjectName("statusBadge")
        self.lbl_status.setProperty("status", "disconnected")
        self.lbl_status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        header.addWidget(self.lbl_model)
        header.addStretch()
        header.addWidget(self.lbl_status)
        layout.addLayout(header)

        # ── Separator ────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        # ── Info rows ────────────────────────────────────────
        self.row_serial   = InfoRow("Serial",           parent=self)
        self.row_android  = InfoRow("Android Version",  parent=self)
        self.row_oneui    = InfoRow("One UI / MIUI",    parent=self)
        self.row_csc      = InfoRow("CSC",              parent=self)
        self.row_imei     = InfoRow("IMEI",             parent=self)
        self.row_battery  = InfoRow("Battery",          parent=self)
        self.row_ram      = InfoRow("RAM",              parent=self)
        self.row_storage  = InfoRow("Storage",          parent=self)
        self.row_knox     = InfoRow("Knox Status",      parent=self)
        self.row_bootldr  = InfoRow("Bootloader",       parent=self)
        self.row_root     = InfoRow("Root Status",      parent=self)

        for row in (
            self.row_serial, self.row_android, self.row_oneui,
            self.row_csc, self.row_imei, self.row_battery,
            self.row_ram, self.row_storage,
            self.row_knox, self.row_bootldr, self.row_root,
        ):
            layout.addWidget(row)

        # ── Refresh button ───────────────────────────────────
        self.btn_refresh = QPushButton("⟳  Refresh Device Info")
        self.btn_refresh.setObjectName("primaryBtn")
        self.btn_refresh.clicked.connect(self.refresh_requested)
        layout.addWidget(self.btn_refresh)

    # ── Public API ───────────────────────────────────────────

    def update_from_device_info(self, info) -> None:
        """Populate all fields from a DeviceInfo object."""
        self.lbl_model.setText(
            f"{info.brand} {info.model}" if info.model else "Unknown Device"
        )
        self._set_status(info.device_state)

        self.row_serial.set_value(info.serial)
        self.row_android.set_value(f"Android {info.android_version}  (SDK {info.sdk_version})")
        self.row_oneui.set_value(info.one_ui_version or "—")
        self.row_csc.set_value(info.csc)
        self.row_imei.set_value(info.imei or "—")
        self.row_battery.set_value(
            f"{info.battery_level}%  Health: {info.battery_health}"
        )
        self.row_ram.set_value(
            f"Total {info.total_ram}  •  Free {info.avail_ram}"
        )
        self.row_storage.set_value(
            f"Total {info.total_storage}  •  Free {info.avail_storage}"
        )
        self.row_knox.set_value(info.knox_status)
        self.row_bootldr.set_value(info.bootloader_status)
        self.row_root.set_value(info.root_status)

    def _set_status(self, state: str) -> None:
        if state == "device":
            self.lbl_status.setText("●  Connected")
            self.lbl_status.setProperty("status", "connected")
        else:
            self.lbl_status.setText("●  " + (state.capitalize() or "Disconnected"))
            self.lbl_status.setProperty("status", "disconnected")
        # Force style refresh
        self.lbl_status.style().unpolish(self.lbl_status)
        self.lbl_status.style().polish(self.lbl_status)

    def reset(self) -> None:
        self.lbl_model.setText("No Device Connected")
        self._set_status("disconnected")
        for row in (
            self.row_serial, self.row_android, self.row_oneui,
            self.row_csc, self.row_imei, self.row_battery,
            self.row_ram, self.row_storage,
            self.row_knox, self.row_bootldr, self.row_root,
        ):
            row.set_value("—")


# Make InfoRow importable without circular imports
from PySide6.QtWidgets import QWidget
