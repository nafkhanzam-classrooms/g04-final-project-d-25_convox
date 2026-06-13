"""Chat area widget rendering message bubbles in a scrollable list."""

from typing import Iterable

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

from gui.models.message_model import Message, MessageKind
from gui.styles import colors
from gui.widgets.message_bubble import MessageBubble
from utils.logger import get_logger


class ChatArea(QWidget):
    """Scrollable list of message bubbles with auto-scroll and clear support."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.logger = get_logger("ChatArea")
        self._build()

    # ---------------------------------------------------------------- building
    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ background-color: {colors.BG_DEEPEST}; border: none; }}"
        )

        self._container = QWidget()
        self._container.setStyleSheet(
            f"background-color: {colors.BG_DEEPEST};"
        )
        self._stack = QVBoxLayout(self._container)
        self._stack.setContentsMargins(0, 8, 0, 8)
        self._stack.setSpacing(2)
        self._stack.addStretch(1)

        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll)

    # ----------------------------------------------------------------- public
    def clear(self) -> None:
        while self._stack.count() > 1:  # keep the trailing stretch
            item = self._stack.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()

    def render_messages(self, messages: Iterable[Message]) -> None:
        self.clear()
        for msg in messages:
            self._append_bubble(msg)
        QTimer.singleShot(0, self._scroll_to_bottom)

    def add_message_obj(self, message: Message) -> None:
        self._append_bubble(message)
        QTimer.singleShot(0, self._scroll_to_bottom)

    # Compatibility helpers used by older code paths -------------------------
    def add_message(self, sender: str, content: str, timestamp: str = "") -> None:
        self.add_message_obj(
            Message(sender=sender, content=content, timestamp=timestamp, kind=MessageKind.NORMAL)
        )

    def add_self_message(self, content: str, timestamp: str = "") -> None:
        self.add_message_obj(
            Message(sender="me", content=content, timestamp=timestamp, kind=MessageKind.SELF)
        )

    def add_system_message(self, message: str) -> None:
        self.add_message_obj(Message(sender="system", content=message, kind=MessageKind.SYSTEM))

    def add_private_message(self, sender: str, content: str, timestamp: str = "", outgoing: bool = False) -> None:
        self.add_message_obj(
            Message(
                sender=sender,
                content=content,
                timestamp=timestamp,
                kind=MessageKind.SELF if outgoing else MessageKind.PRIVATE,
                target_user=sender if outgoing else None,
            )
        )

    # ---------------------------------------------------------------- helpers
    def _append_bubble(self, message: Message) -> None:
        bubble = MessageBubble(message)
        # insert before the trailing stretch
        self._stack.insertWidget(self._stack.count() - 1, bubble)

    def _scroll_to_bottom(self) -> None:
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.maximum())
