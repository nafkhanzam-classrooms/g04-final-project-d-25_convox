"""Single chat message bubble widget."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from gui.models.message_model import Message, MessageKind
from gui.styles import colors


_BUBBLE_COLORS = {
    MessageKind.SELF: colors.SELF_BUBBLE,
    MessageKind.NORMAL: colors.OTHER_BUBBLE,
    MessageKind.SYSTEM: colors.SYSTEM_BUBBLE,
    MessageKind.PRIVATE: colors.PRIVATE_BUBBLE,
    MessageKind.FILE: colors.OTHER_BUBBLE,
    MessageKind.IMAGE: colors.OTHER_BUBBLE,
}


class MessageBubble(QWidget):
    """A single chat-line rendered as a Discord-style bubble."""

    def __init__(self, message: Message, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.message = message
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self._build()

    def _build(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 4, 10, 4)
        outer.setSpacing(0)

        if self.message.is_system:
            self._build_system(outer)
            return

        bubble = QFrame()
        bubble.setObjectName("bubble")
        bubble.setStyleSheet(self._bubble_style())
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(12, 8, 12, 8)
        bubble_layout.setSpacing(4)

        header_text = self._header_text()
        if header_text:
            header = QLabel(header_text)
            header.setStyleSheet(
                f"color: {colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;"
            )
            bubble_layout.addWidget(header)

        body = QLabel(self.message.content)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body.setStyleSheet(f"color: {colors.TEXT_PRIMARY}; font-size: 13px;")
        bubble_layout.addWidget(body)

        bubble.setMaximumWidth(640)

        if self.message.is_self:
            outer.addStretch(1)
            outer.addWidget(bubble, 0, Qt.AlignmentFlag.AlignRight)
        else:
            outer.addWidget(bubble, 0, Qt.AlignmentFlag.AlignLeft)
            outer.addStretch(1)

    def _build_system(self, outer: QHBoxLayout) -> None:
        label = QLabel(self.message.content)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setItalic(True)
        label.setFont(font)
        label.setStyleSheet(
            f"color: {colors.TEXT_MUTED}; padding: 4px; font-size: 11px;"
        )
        outer.addStretch(1)
        outer.addWidget(label)
        outer.addStretch(1)

    def _bubble_style(self) -> str:
        bg = _BUBBLE_COLORS.get(self.message.kind, colors.OTHER_BUBBLE)
        return (
            f"#bubble {{ background-color: {bg}; border-radius: 10px; }}"
        )

    def _header_text(self) -> str:
        parts: list[str] = []
        if self.message.is_private:
            target = self.message.target_user or ""
            if self.message.is_self and target:
                parts.append(f"to {target} (private)")
            else:
                parts.append(f"{self.message.sender} (private)")
        elif not self.message.is_self:
            parts.append(self.message.sender)
        if self.message.timestamp:
            parts.append(self.message.timestamp)
        return "  •  ".join(parts)
