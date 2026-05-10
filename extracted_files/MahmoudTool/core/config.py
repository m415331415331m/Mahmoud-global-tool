"""
core/config.py
──────────────
Application configuration manager (JSON-backed).
"""

import json
from pathlib import Path
from typing import Any


_DEFAULTS: dict[str, Any] = {
    "language": "ar",
    "theme": "dark",
    "adb_path": "adb",
    "fastboot_path": "fastboot",
    "scrcpy_path": "scrcpy",
    "auto_detect_device": True,
    "refresh_interval_ms": 2000,
    "log_level": "INFO",
    "update_channel": "stable",
    "plugin_dir": "plugins",
    "firmware_dir": "firmware",
    "backup_dir": "backups",
    "show_notifications": True,
}


class AppConfig:
    """
    Persistent JSON-based configuration with attribute-style access.

    Usage:
        cfg = AppConfig(Path("config.json"))
        cfg.language       # -> "ar"
        cfg.set("theme", "light")
        cfg.save()
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._data: dict[str, Any] = dict(_DEFAULTS)
        self._load()

    # ── I/O ──────────────────────────────────────────────────

    def _load(self) -> None:
        if self._path.exists():
            try:
                loaded = json.loads(self._path.read_text(encoding="utf-8"))
                self._data.update(loaded)
            except (json.JSONDecodeError, OSError):
                pass  # use defaults

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── Access ───────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def __getattr__(self, key: str) -> Any:
        if key.startswith("_"):
            raise AttributeError(key)
        return self._data.get(key)

    def all(self) -> dict[str, Any]:
        return dict(self._data)
