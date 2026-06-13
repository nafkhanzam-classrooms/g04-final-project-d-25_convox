"""Convox desktop application bootstrap."""

import sys
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from gui.styles.theme import apply_theme
from gui.windows.login_window import LoginWindow
from utils.logger import get_logger


class ConvoxGuiApp:
    """High-level launcher for the Convox PyQt6 client."""

    def __init__(self) -> None:
        self.logger = get_logger("ConvoxGuiApp")
        # Reuse existing instance when embedded (e.g. tests).
        existing = QApplication.instance()
        if existing is not None:
            self.app = existing
        else:
            self.app = QApplication(sys.argv)
        self.app.setApplicationName("Convox")
        self.app.setOrganizationName("Convox")
        apply_theme(self.app)

        self.login_window: Optional[LoginWindow] = None

    def run(self) -> int:
        self.logger.info("Starting Convox GUI Application")
        self.login_window = LoginWindow()
        self.login_window.show()
        return self.app.exec()

    def quit(self) -> None:
        self.logger.info("Shutting down Convox GUI Application")
        if self.login_window is not None:
            self.login_window.close()
        self.app.quit()


def main() -> None:
    app = ConvoxGuiApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
