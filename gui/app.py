"""Main GUI application for Convox."""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from gui.windows.login_window import LoginWindow
from utils.logger import get_logger


class ConvoxGuiApp:
    """Main GUI application class."""

    def __init__(self):
        self.logger = get_logger("ConvoxGuiApp")
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.login_window = None

    def run(self) -> int:
        """Run the application."""
        self.logger.info("Starting Convox GUI Application")

        # Create and show login window
        self.login_window = LoginWindow()
        self.login_window.show()

        # Run event loop
        return self.app.exec()

    def quit(self) -> None:
        """Quit the application."""
        self.logger.info("Shutting down Convox GUI Application")
        if self.login_window:
            self.login_window.close()
        self.app.quit()


def main():
    """Entry point."""
    app = ConvoxGuiApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
