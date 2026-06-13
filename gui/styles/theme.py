"""Loader that turns the QSS template into a finished stylesheet."""

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import QApplication

from gui.styles import colors

_QSS_PATH = Path(__file__).with_name("theme.qss")


def load_theme() -> str:
    """Load theme.qss and substitute color tokens from colors.py."""
    text = _QSS_PATH.read_text(encoding="utf-8")
    for name, value in vars(colors).items():
        if name.isupper() and isinstance(value, str):
            text = text.replace(f"@{name}@", value)
    return text


def apply_theme(app: Optional[QApplication] = None) -> None:
    """Apply the dark theme to a QApplication (defaults to the active one)."""
    target = app or QApplication.instance()
    if target is not None:
        target.setStyleSheet(load_theme())
