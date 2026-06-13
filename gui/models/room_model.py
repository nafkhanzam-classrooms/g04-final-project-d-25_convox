"""Room dataclass used by the room sidebar and chat area."""

from dataclasses import dataclass, field
from typing import List

from gui.models.message_model import Message


@dataclass
class Room:
    """A chat room known to the GUI."""

    name: str
    owner: str = "system"
    members: List[str] = field(default_factory=list)
    max_capacity: int = 50
    visibility: str = "public"
    voice_active: bool = False
    voice_participants: List[str] = field(default_factory=list)
    messages: List[Message] = field(default_factory=list)
    unread_count: int = 0

    def is_member(self, username: str) -> bool:
        return username in self.members

    def add_message(self, message: Message) -> None:
        self.messages.append(message)

    def increment_unread(self) -> None:
        self.unread_count += 1

    def clear_unread(self) -> None:
        self.unread_count = 0
