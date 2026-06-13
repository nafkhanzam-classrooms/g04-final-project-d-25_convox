"""Models package - plain dataclasses describing client-side state."""

from gui.models.app_model import ApplicationModel, FileTransfer
from gui.models.message_model import Message, MessageKind
from gui.models.room_model import Room
from gui.models.user_model import Friend, User, UserStatus

__all__ = [
    "ApplicationModel",
    "FileTransfer",
    "Friend",
    "Message",
    "MessageKind",
    "Room",
    "User",
    "UserStatus",
]
