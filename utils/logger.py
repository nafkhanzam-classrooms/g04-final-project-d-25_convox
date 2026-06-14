"""Centralised logging helpers for Convox.

Two public surfaces:

* ``get_logger(name)`` - the original API; every existing caller keeps
  working unchanged.
* ``get_category_logger(category, name)`` - a thin wrapper that prefixes
  log records with a category tag (``[VOICE]``, ``[TRANSFER]``, etc.).

Categories are useful for filtering ``server_activity.log`` after a demo
run without changing the format the rest of the code relies on.
"""

from __future__ import annotations

import logging
import os
from typing import Iterable

LOG_FILE = os.path.join(os.path.dirname(__file__), "../server_activity.log")

_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

# Useful named categories. Free-form strings are accepted as well; this
# tuple just documents the intended set.
CATEGORIES: tuple[str, ...] = ("INFO", "WARN", "ERROR", "VOICE", "TRANSFER", "AUTH", "NETWORK")


def _ensure_handlers(logger: logging.Logger) -> None:
    if logger.handlers:
        return

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(_FORMAT, _DATEFMT)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

    try:
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        # Disk-not-writable (e.g. in a sandbox); console-only is fine.
        pass


def get_logger(name: str) -> logging.Logger:
    """Return a Convox logger.

    Multiple calls with the same ``name`` return the same instance, so
    handlers are attached at most once.
    """
    logger = logging.getLogger(name)
    _ensure_handlers(logger)
    return logger


def get_category_logger(category: str, name: str | None = None) -> logging.LoggerAdapter:
    """Return a LoggerAdapter that prepends ``[<category>]`` to messages.

    Example::

        log = get_category_logger("VOICE", "UDPVoiceServer")
        log.info("user joined room %s", room)
        # → "... UDPVoiceServer: [VOICE] user joined room global"
    """
    base = get_logger(name or category)
    return _CategoryAdapter(base, {"category": category.upper()})


class _CategoryAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        category = self.extra.get("category", "INFO")
        return f"[{category}] {msg}", kwargs


def list_categories() -> Iterable[str]:
    return CATEGORIES
