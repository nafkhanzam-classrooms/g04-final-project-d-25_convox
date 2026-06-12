"""Chat area widget showing messages."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PyQt6.QtGui import QFont, QColor, QTextCursor
from PyQt6.QtCore import Qt

from utils.logger import get_logger


class ChatArea(QWidget):
    """Central chat display area."""

    def __init__(self):
        super().__init__()
        self.logger = get_logger("ChatArea")
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: none;
                font-size: 12px;
                font-family: "Courier New", monospace;
            }
            QTextEdit:focus {
                outline: none;
            }
        """)

        layout.addWidget(self.chat_display)
        self.setLayout(layout)

    def add_message(self, sender: str, content: str, timestamp: str) -> None:
        """Add regular message to chat."""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # Format: [timestamp] sender: content
        format_text = f"[{timestamp}] {sender}: {content}\n"

        cursor.insertText(format_text)
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )

    def add_system_message(self, message: str) -> None:
        """Add system message (styled differently)."""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        format_text = f"[SYSTEM] {message}\n"

        cursor.insertText(format_text)
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )

    def clear(self) -> None:
        """Clear chat display."""
        self.chat_display.clear()

    def get_content(self) -> str:
        """Get all chat content."""
        return self.chat_display.toPlainText()
