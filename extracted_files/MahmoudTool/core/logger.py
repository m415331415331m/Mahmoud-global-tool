"""
core/logger.py
──────────────
Centralised logging setup using Python's standard logging + loguru-style format.
Writes to logs/tool_YYYY-MM-DD.log and to the console.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path


LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)-28s | %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(log_dir: Path, level: str = "DEBUG") -> logging.Logger:
    """
    Configure root logger.

    Parameters
    ----------
    log_dir : Path  Directory where log files are written.
    level   : str   Logging level (DEBUG / INFO / WARNING / ERROR).

    Returns
    -------
    logging.Logger  The configured root logger.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"tool_{today}.log"

    numeric_level = getattr(logging, level.upper(), logging.DEBUG)

    root = logging.getLogger()
    root.setLevel(numeric_level)

    # ── File handler ─────────────────────────────────────────
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(numeric_level)
    fh.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    # ── Stream handler ───────────────────────────────────────
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    root.addHandler(fh)
    root.addHandler(sh)

    root.info("Logger initialised → %s", log_file)
    return root


def get_logger(name: str) -> logging.Logger:
    """Return a named child logger."""
    return logging.getLogger(name)
