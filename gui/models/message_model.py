"""Chat message dataclass used by the chat area."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MessageKind(str, Enum):
    NORMAL = "NORMAL"
    SELF = "SELF"
    SYSTEM = "SYSTEM"
    PRIVATE = "PRIVATE"
    FILE = "FILE"
    IMAGE = "IMAGE"


@dataclass
class Message:
    """A rendered chat message."""

    sender: str
    content: str
    timestamp: str = ""
    room: Optional[str] = None
    target_user: Optional[str] = None
    kind: MessageKind = MessageKind.NORMAL
    file_path: Optional[str] = None
    filename: Optional[str] = None

    @property
    def is_system(self) -> bool:
        return self.kind == MessageKind.SYSTEM

    @property
    def is_self(self) -> bool:
        return self.kind == MessageKind.SELF

    @property
    def is_private(self) -> bool:
        return self.kind == MessageKind.PRIVATE

    def display_text(self) -> str:
        if self.is_system:
            return f"[SYSTEM] {self.content}"
        prefix = f"[{self.timestamp}] " if self.timestamp else ""
        return f"{prefix}{self.sender}: {self.content}"
