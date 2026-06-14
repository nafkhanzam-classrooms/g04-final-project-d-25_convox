"""Centralized event dispatcher for signal-slot communication."""

from PyQt6.QtCore import QObject, pyqtSignal
from typing import Any, Dict


class EventDispatcher(QObject):
    """Central event hub for all realtime GUI updates from networking threads."""

    # Connection events
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    connection_error = pyqtSignal(str)

    # Authentication events
    login_success = pyqtSignal(str)  # username
    login_failed = pyqtSignal(str)  # error message
    register_success = pyqtSignal(str)  # username
    session_restored = pyqtSignal(str, str)  # username, room

    # Message events
    message_received = pyqtSignal(str, str, str, str)  # room, sender, message, timestamp
    private_message_received = pyqtSignal(str, str, str)  # sender, message, timestamp
    system_message = pyqtSignal(str, str)  # room, message

    # Room events
    room_created = pyqtSignal(str)  # room_name
    room_joined = pyqtSignal(str)  # room_name
    room_left = pyqtSignal(str)  # room_name
    room_deleted = pyqtSignal(str)  # room_name
    room_list_updated = pyqtSignal(list)  # [room_names]

    # User presence events
    user_online = pyqtSignal(str)  # username
    user_offline = pyqtSignal(str)  # username
    user_status_changed = pyqtSignal(str, str)  # username, status
    online_users_updated = pyqtSignal(list)  # [usernames]

    # Friend events
    friend_request_received = pyqtSignal(str)  # from_user
    friend_request_accepted = pyqtSignal(str)  # friend_name
    friend_list_updated = pyqtSignal(list)  # [friend_dicts]

    # Voice events
    voice_started = pyqtSignal(str)  # room_name
    voice_stopped = pyqtSignal(str)  # room_name
    voice_user_joined = pyqtSignal(str, str)  # room, username
    voice_user_left = pyqtSignal(str, str)  # room, username
    user_speaking = pyqtSignal(str, str)  # room, username
    user_muted = pyqtSignal(str, str)  # room, username
    user_unmuted = pyqtSignal(str, str)  # room, username

    # Matchmaking events
    matchmaking_queue_joined = pyqtSignal()
    matchmaking_queue_left = pyqtSignal()
    matchmaking_found = pyqtSignal(str, list)  # room_name, participants

    # File transfer events
    file_transfer_started = pyqtSignal(str, str, int)  # transfer_id, filename, filesize
    file_transfer_progress = pyqtSignal(str, int)  # transfer_id, progress_percent
    file_transfer_complete = pyqtSignal(str)  # transfer_id
    file_transfer_error = pyqtSignal(str, str)  # transfer_id, error_message

    # Image events
    image_received = pyqtSignal(str, str, str)  # room_or_sender, filename, file_path

    # Error events
    error = pyqtSignal(str)  # error_message

    def __init__(self):
        super().__init__()


# Global event dispatcher instance
_dispatcher: Dict[str, EventDispatcher] = {}


def get_dispatcher() -> EventDispatcher:
    """Get or create the global event dispatcher."""
    if "default" not in _dispatcher:
        _dispatcher["default"] = EventDispatcher()
    return _dispatcher["default"]


def reset_dispatcher() -> None:
    """Reset the global dispatcher (for testing)."""
    if "default" in _dispatcher:
        _dispatcher.clear()
