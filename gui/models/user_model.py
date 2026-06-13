"""User and presence-related dataclasses."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class UserStatus(str, Enum):
    """User presence statuses (mirrors backend presence.status_manager)."""

    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    IN_ROOM = "IN_ROOM"
    IN_MATCH = "IN_MATCH"
    DO_NOT_DISTURB = "DO_NOT_DISTURB"
    VOICE_ACTIVE = "VOICE_ACTIVE"

    @classmethod
    def coerce(cls, value: object) -> "UserStatus":
        """Best-effort conversion from arbitrary input to UserStatus."""
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).upper())
        except ValueError:
            return cls.OFFLINE


@dataclass
class User:
    """A user known to the GUI client."""

    username: str
    status: UserStatus = UserStatus.OFFLINE
    in_voice: bool = False
    muted: bool = False
    speaking: bool = False
    last_seen: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "username": self.username,
            "status": self.status.value,
            "in_voice": self.in_voice,
            "muted": self.muted,
            "speaking": self.speaking,
            "last_seen": self.last_seen,
        }


@dataclass
class Friend:
    """A friend entry rendered in the friends panel."""

    username: str
    status: UserStatus = UserStatus.OFFLINE
    in_voice: bool = False
    pending: bool = False  # incoming request not yet accepted

    def to_dict(self) -> Dict[str, object]:
        return {
            "username": self.username,
            "status": self.status.value,
            "in_voice": self.in_voice,
            "pending": self.pending,
        }
