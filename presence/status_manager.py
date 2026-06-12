import threading
from enum import Enum
from typing import Dict, Optional

from database.db import Database
from protocol.packet import PacketType
from server.connection_manager import ConnectionManager
from utils.logger import get_logger


class UserStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    IN_ROOM = "IN_ROOM"
    IN_MATCH = "IN_MATCH"
    DO_NOT_DISTURB = "DO_NOT_DISTURB"


class StatusManager:
    def __init__(self, database: Database, connection_manager: ConnectionManager):
        self.database = database
        self.connection_manager = connection_manager
        self.status_map: Dict[str, UserStatus] = {}
        self.lock = threading.RLock()
        self.logger = get_logger("StatusManager")

    def set_status(self, username: str, status: UserStatus) -> None:
        with self.lock:
            self.status_map[username] = status
            self.database.update_user_status(username, status.value)
            self._notify_friends(username, status)

    def get_status(self, username: str) -> UserStatus:
        with self.lock:
            return self.status_map.get(username, UserStatus.OFFLINE)

    def remove(self, username: str) -> None:
        with self.lock:
            self.status_map.pop(username, None)
            self.database.update_user_status(username, UserStatus.OFFLINE.value)

    def _notify_friends(self, username: str, status: UserStatus) -> None:
        friends = self.database.list_friends(username)
        for friend_record in friends:
            friend_name = friend_record["friend_name"]
            if self.connection_manager.get(friend_name):
                self.connection_manager.send(
                    friend_name,
                    PacketType.STATUS_UPDATE,
                    user=username,
                    status=status.value,
                )
