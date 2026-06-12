from typing import Optional

from database.db import Database
from protocol.packet import PacketType
from server.connection_manager import ConnectionManager
from utils.logger import get_logger


class FriendRequestHandler:
    def __init__(self, database: Database, connection_manager: ConnectionManager):
        self.database = database
        self.connection_manager = connection_manager
        self.logger = get_logger("FriendRequestHandler")

    def send_request(self, sender: str, receiver: str) -> None:
        if sender == receiver:
            raise ValueError("Cannot add yourself as a friend.")

        receiver_id = self.database.find_user_id(receiver)
        if receiver_id is None:
            raise ValueError(f"User '{receiver}' does not exist.")

        sender_id = self.database.get_or_create_user(sender)
        if self.database.are_friends(sender, receiver):
            raise ValueError(f"{receiver} is already your friend.")

        if self.database.friend_request_exists(sender, receiver):
            raise ValueError("A friend request is already pending.")

        self.database.create_friend_request(sender, receiver)
        target_conn = self.connection_manager.get(receiver)
        if target_conn:
            self.connection_manager.send(
                receiver,
                PacketType.FRIEND_REQUEST,
                sender=sender,
                message=f"Friend request from {sender}",
            )
        self.logger.info("Friend request sent from %s to %s", sender, receiver)

    def accept_request(self, receiver: str, sender: str) -> None:
        if not self.database.friend_request_exists(sender, receiver):
            raise ValueError(f"No pending friend request from {sender}." )

        self.database.respond_friend_request(sender, receiver, accept=True)
        self.logger.info("%s accepted friend request from %s", receiver, sender)
        self.connection_manager.send(
            sender,
            PacketType.SYSTEM,
            message=f"{receiver} accepted your friend request.",
        )
        self.connection_manager.send(
            receiver,
            PacketType.SYSTEM,
            message=f"You are now friends with {sender}.",
        )

    def reject_request(self, receiver: str, sender: str) -> None:
        if not self.database.friend_request_exists(sender, receiver):
            raise ValueError(f"No pending friend request from {sender}." )

        self.database.respond_friend_request(sender, receiver, accept=False)
        self.logger.info("%s rejected friend request from %s", receiver, sender)
        self.connection_manager.send(
            sender,
            PacketType.SYSTEM,
            message=f"{receiver} rejected your friend request.",
        )
        self.connection_manager.send(
            receiver,
            PacketType.SYSTEM,
            message=f"You rejected the friend request from {sender}.",
        )
