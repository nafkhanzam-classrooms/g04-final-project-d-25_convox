"""Lightweight standalone chat window.

Useful for testing the chat area in isolation. The dashboard hosts the
full layout; this window offers a stripped-down "chat-only" view that
shares the same widgets and controllers.
"""

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.controllers.event_dispatcher import get_dispatcher
from gui.controllers.gui_state_manager import GuiStateManager
from gui.controllers.tcp_controller import TCPController
from gui.models.app_model import ApplicationModel
from gui.styles import colors
from gui.widgets.chat_area import ChatArea
from utils.logger import get_logger


class ChatWindow(QMainWindow):
    """Single-room chat-only window."""

    def __init__(
        self,
        tcp_controller: TCPController,
        username: str,
        room: str = "global",
        model: Optional[ApplicationModel] = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.logger = get_logger("ChatWindow")
        self.tcp_controller = tcp_controller
        self.username = username
        self.room = room
        self.dispatcher = get_dispatcher()
        self.model = model or ApplicationModel()
        self.model.set_username(username)
        self.state_manager = GuiStateManager(self.model, self.dispatcher)
        self.state_manager.set_identity(username)
        self.state_manager.set_current_room(room)

        self.setWindowTitle(f"Convox Chat - #{room}")
        self.resize(720, 600)
        self._build()
        self.state_manager.message_added.connect(self._on_message_added)

    def _build(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel(f"# {self.room}")
        header.setFixedHeight(44)
        header.setContentsMargins(20, 0, 20, 0)
        header.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        header.setStyleSheet(
            f"background-color: {colors.BG_DEEPEST}; color: {colors.TEXT_PRIMARY}; "
            f"font-size: 14px; font-weight: 700; "
            f"border-bottom: 1px solid {colors.BORDER_SOFT};"
        )
        layout.addWidget(header)

        self.chat_area = ChatArea()
        layout.addWidget(self.chat_area, 1)

        row = QHBoxLayout()
        row.setContentsMargins(14, 12, 14, 14)
        row.setSpacing(8)

        self.input = QLineEdit()
        self.input.setPlaceholderText(f"Message #{self.room}")
        self.input.setMinimumHeight(38)
        self.input.returnPressed.connect(self._send)
        row.addWidget(self.input, 1)

        send = QPushButton("Send")
        send.setMinimumHeight(38)
        send.clicked.connect(self._send)
        row.addWidget(send)
        layout.addLayout(row)

        self.chat_area.render_messages(self.model.get_room_messages(self.room))

    def _send(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.tcp_controller.send_message(self.room, text)
        # Server echoes the message back; let the dispatcher render it.
        self.input.clear()

    def _on_message_added(self, target: str) -> None:
        if target == self.room:
            self.chat_area.render_messages(self.model.get_room_messages(self.room))
