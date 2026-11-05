"""Logging setup using stdlib ``logging``. Called from entry points only (never at import)."""

from __future__ import annotations

import logging

_FORMAT = "%(asctime)s %(levelname)-7s [%(threadName)s] %(name)s: %(message)s"


def configure_logging(level: str) -> None:
    """Configure the root logger for the current process.

    Args:
        level: one of ``constants.LOG_LEVELS`` (already validated by config).
    """
    logging.basicConfig(level=getattr(logging, level), format=_FORMAT, force=True)
