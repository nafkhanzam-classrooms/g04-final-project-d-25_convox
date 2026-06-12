from typing import Any

from database.db import Database
from server.connection_manager import ConnectionManager
from protocol.packet import PacketType


class FriendListManager:
    def __init__(self, database: Database, connection_manager: ConnectionManager):
        self.database = database
        self.connection_manager = connection_manager

    def send_friend_list(self, username: str) -> None:
        friend_records = self.database.list_friends(username)
        friends = [
            {
                "username": record["friend_name"],
                "status": self._presence_status(record["friend_name"]),
            }
            for record in friend_records
        ]
        self.connection_manager.send(
            username,
            PacketType.FRIEND_LIST,
            friends=friends,
        )

    def _presence_status(self, friend_name: str) -> str:
        conn = self.connection_manager.get(friend_name)
        return "ONLINE" if conn else "OFFLINE"

    def remove_friend(self, username: str, friend_name: str) -> None:
        if not self.database.are_friends(username, friend_name):
            raise ValueError(f"{friend_name} is not in your friend list.")

        self.database.remove_friend(username, friend_name)
        self.connection_manager.send(
            username,
            PacketType.SYSTEM,
            message=f"{friend_name} has been removed from your friends.",
        )
