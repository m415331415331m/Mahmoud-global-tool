"""
core/database.py
────────────────
SQLite database manager for device history, operation logs, and profiles.
Thread-safe via connection-per-thread pattern.
"""

import sqlite3
import threading
import logging
from pathlib import Path
from datetime import datetime
from typing import Any


log = logging.getLogger(__name__)

# ── Thread-local storage for connections ─────────────────────
_local = threading.local()


class DatabaseManager:
    """
    Manages an SQLite database with automatic schema creation.

    One connection per thread is maintained via threading.local().
    """

    SCHEMA = """
    -- Device registry ────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS devices (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        serial      TEXT    NOT NULL UNIQUE,
        model       TEXT,
        brand       TEXT,
        android_ver TEXT,
        one_ui_ver  TEXT,
        imei        TEXT,
        csc         TEXT,
        knox_status TEXT,
        root_status TEXT,
        first_seen  TEXT    DEFAULT (datetime('now')),
        last_seen   TEXT    DEFAULT (datetime('now'))
    );

    -- Operation log ───────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS operation_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id   INTEGER REFERENCES devices(id),
        operation   TEXT    NOT NULL,
        status      TEXT    NOT NULL,   -- success / error / pending
        detail      TEXT,
        created_at  TEXT    DEFAULT (datetime('now'))
    );

    -- APN profiles ────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS apn_profiles (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT    NOT NULL,
        apn         TEXT    NOT NULL,
        mcc         TEXT,
        mnc         TEXT,
        type        TEXT,
        protocol    TEXT    DEFAULT 'IPv4v6',
        country     TEXT    DEFAULT 'YE'
    );

    -- Device profiles (backup/restore) ───────────────────────
    CREATE TABLE IF NOT EXISTS device_profiles (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id   INTEGER REFERENCES devices(id),
        profile_name TEXT   NOT NULL,
        data        TEXT,   -- JSON blob
        created_at  TEXT    DEFAULT (datetime('now'))
    );

    -- Settings overrides ──────────────────────────────────────
    CREATE TABLE IF NOT EXISTS settings (
        key   TEXT PRIMARY KEY,
        value TEXT
    );
    """

    _SEED_APNS = [
        ("Yemen Mobile", "yemenmobile",     "421", "01", "default,mms,supl", "IPv4v6", "YE"),
        ("YOU",          "you",             "421", "02", "default,mms,supl", "IPv4v6", "YE"),
        ("Sabafon",      "sabafon",         "421", "03", "default,mms,supl", "IPv4v6", "YE"),
        ("Way",          "way",             "421", "04", "default,mms,supl", "IPv4v6", "YE"),
    ]

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Connection management ────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(_local, "connection") or _local.connection is None:
            _local.connection = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES,
            )
            _local.connection.row_factory = sqlite3.Row
            _local.connection.execute("PRAGMA journal_mode=WAL")
            _local.connection.execute("PRAGMA foreign_keys=ON")
        return _local.connection

    def initialize(self) -> None:
        """Create schema and seed initial data."""
        conn = self._conn()
        conn.executescript(self.SCHEMA)
        conn.commit()
        self._seed_apns()
        log.info("Database initialised at %s", self._db_path)

    def _seed_apns(self) -> None:
        conn = self._conn()
        existing = conn.execute("SELECT COUNT(*) FROM apn_profiles").fetchone()[0]
        if existing == 0:
            conn.executemany(
                "INSERT INTO apn_profiles(name,apn,mcc,mnc,type,protocol,country) VALUES(?,?,?,?,?,?,?)",
                self._SEED_APNS,
            )
            conn.commit()

    # ── Device CRUD ──────────────────────────────────────────

    def upsert_device(self, serial: str, **fields: Any) -> int:
        """Insert or update a device record; returns its id."""
        conn = self._conn()
        existing = conn.execute(
            "SELECT id FROM devices WHERE serial=?", (serial,)
        ).fetchone()

        now = datetime.now().isoformat(sep=" ", timespec="seconds")
        if existing:
            set_clause = ", ".join(f"{k}=?" for k in fields)
            values = list(fields.values()) + [now, serial]
            conn.execute(
                f"UPDATE devices SET {set_clause}, last_seen=? WHERE serial=?",
                values,
            )
            conn.commit()
            return existing["id"]
        else:
            fields["serial"] = serial
            fields["first_seen"] = now
            fields["last_seen"] = now
            cols = ", ".join(fields.keys())
            placeholders = ", ".join("?" * len(fields))
            cur = conn.execute(
                f"INSERT INTO devices({cols}) VALUES({placeholders})",
                list(fields.values()),
            )
            conn.commit()
            return cur.lastrowid

    def get_devices(self) -> list[sqlite3.Row]:
        return self._conn().execute(
            "SELECT * FROM devices ORDER BY last_seen DESC"
        ).fetchall()

    # ── Operation Log ────────────────────────────────────────

    def log_operation(
        self,
        operation: str,
        status: str,
        detail: str = "",
        device_id: int | None = None,
    ) -> None:
        self._conn().execute(
            "INSERT INTO operation_log(device_id,operation,status,detail) VALUES(?,?,?,?)",
            (device_id, operation, status, detail),
        )
        self._conn().commit()

    def get_operations(self, limit: int = 200) -> list[sqlite3.Row]:
        return self._conn().execute(
            "SELECT ol.*, d.model, d.serial FROM operation_log ol "
            "LEFT JOIN devices d ON d.id=ol.device_id "
            "ORDER BY ol.created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

    # ── APN Profiles ─────────────────────────────────────────

    def get_apn_profiles(self, country: str = "YE") -> list[sqlite3.Row]:
        return self._conn().execute(
            "SELECT * FROM apn_profiles WHERE country=?", (country,)
        ).fetchall()

    # ── Settings ─────────────────────────────────────────────

    def get_setting(self, key: str, default: str = "") -> str:
        row = self._conn().execute(
            "SELECT value FROM settings WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self._conn().execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self._conn().commit()
