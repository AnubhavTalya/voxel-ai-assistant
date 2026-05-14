"""
utils/logger.py — Structured rotating log with console + file handlers.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "voxel",
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
    max_bytes: int = 5 * 1024 * 1024,   # 5 MB
    backup_count: int = 3,
) -> logging.Logger:
    """
    Create and configure a named logger with:
      - Coloured console output (stdout)
      - Rotating file handler (optional)
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger   # already configured (re-entrant safe)

    fmt_console = "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s"
    fmt_file    = "%(asctime)s  %(levelname)-8s  %(name)s  [%(filename)s:%(lineno)d]  %(message)s"
    datefmt = "%H:%M:%S"

    # ── Console handler ──────────────────────────────────────────────────────
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(_ColorFormatter(fmt_console, datefmt=datefmt))
    logger.addHandler(ch)

    # ── File handler (optional) ──────────────────────────────────────────────
    if log_file is not None:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        fh.setLevel(logging.DEBUG)   # always verbose in file
        fh.setFormatter(logging.Formatter(fmt_file, datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(fh)

    logger.propagate = False
    return logger


class _ColorFormatter(logging.Formatter):
    """ANSI colour codes for log level — looks great in any modern terminal."""

    COLORS = {
        logging.DEBUG:    "\033[36m",    # cyan
        logging.INFO:     "\033[32m",    # green
        logging.WARNING:  "\033[33m",    # yellow
        logging.ERROR:    "\033[31m",    # red
        logging.CRITICAL: "\033[1;31m",  # bold red
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, "")
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)
