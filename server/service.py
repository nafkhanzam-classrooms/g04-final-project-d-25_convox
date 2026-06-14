import base64
import threading
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from database.db import Database
from friends.friend_list import FriendListManager
from friends.request_handler import FriendRequestHandler
from matchmaking.matchmaker import Matchmaker
from media.encoder import decode_bytes
from media.image_transfer import MAX_IMAGE_SIZE, save_image, validate_image
from presence.status_manager import StatusManager, UserStatus
from protocol.chunking.chunk_manager import ChunkManager, generate_transfer_id
from protocol.packet import PacketType
from rooms.room_manager import RoomManager
from scheduler.scheduled_broadcast import ScheduledBroadcastRunner
from server.auth import AuthService
from server.connection_manager import ConnectionManager
from server.session_manager import SessionManager
from storage.storage_manager import StorageManager
from voice.voice_room import VoiceRoomManager
from utils.helper import timestamp
from utils.logger import get_logger


class ConvoxService:
    def __init__(self) -> None:
        self.database = Database()
        self.connections = ConnectionManager()
        self.status_manager = StatusManager(self.database, self.connections)
        self.room_manager = RoomManager(self.database)
        self.friend_requests = FriendRequestHandler(self.database, self.connections)
        self.friend_list = FriendListManager(self.database, self.connections)
        self.matchmaker = Matchmaker()
        self.chunk_manager = ChunkManager()
        self.scheduler = ScheduledBroadcastRunner(self.database, self.dispatch_scheduled_broadcast)
        self.session_manager = SessionManager(self.database)
        self.auth_service = AuthService(self.database)
        self.storage_manager = StorageManager()
        self.voice_room_manager = VoiceRoomManager()
        self.user_rooms: Dict[str, str] = {}
        self.active_sessions: Dict[str, str] = {}
        self.lock = threading.RLock()
        self.logger = get_logger("ConvoxService")

    def register_client(self, username: str, skip_welcome: bool = False) -> None:
        self.database.get_or_create_user(username)
        self.status_manager.set_status(username, UserStatus.ONLINE)
        if username not in self.user_rooms:
            self.user_rooms[username] = "global"
        room, error = self.room_manager.join_room(self.user_rooms[username], username)
        if error:
            raise ValueError(f"Failed to join room {self.user_rooms[username]}: {error}")
        if not skip_welcome:
            self.send_system(username, f"Welcome to Convox, {username}!", room=self.user_rooms[username])
            self.broadcast_system(f"{username} joined {self.user_rooms[username]}.", room=self.user_rooms[username])
            self.send_online_users()
            self.send_pending_friend_requests(username)

    def route_packet(self, packet: Dict[str, Any], username: str) -> None:
        packet_type = packet.get("type")
        try:
            if packet_type == PacketType.MESSAGE.value:
                self.handle_room_message(username, packet)
            elif packet_type == PacketType.PRIVATE_MESSAGE.value:
                self.handle_private_message(username, packet)
            elif packet_type == PacketType.CREATE_ROOM.value:
                self.handle_create_room(username, packet)
            elif packet_type == PacketType.JOIN_ROOM.value:
                self.handle_join_room(username, packet)
            elif packet_type == PacketType.LEAVE_ROOM.value:
                self.handle_leave_room(username, packet)
            elif packet_type == PacketType.INVITE_USER.value:
                self.handle_invite_user(username, packet)
            elif packet_type == PacketType.KICK_USER.value:
                self.handle_kick_user(username, packet)
            elif packet_type == PacketType.DELETE_ROOM.value:
                self.handle_delete_room(username, packet)
            elif packet_type == PacketType.GET_FRIENDS.value:
                self.friend_list.send_friend_list(username)
            elif packet_type == PacketType.ADD_FRIEND.value:
                self.friend_requests.send_request(username, str(packet.get("friend", "")).strip())
            elif packet_type == PacketType.ACCEPT_FRIEND.value:
                self.friend_requests.accept_request(username, str(packet.get("friend", "")).strip())
            elif packet_type == PacketType.REJECT_FRIEND.value:
                self.friend_requests.reject_request(username, str(packet.get("friend", "")).strip())
            elif packet_type == PacketType.REMOVE_FRIEND.value:
                self.friend_list.remove_friend(username, str(packet.get("friend", "")).strip())
            elif packet_type == PacketType.GET_ONLINE_USERS.value:
                self.send_online_users(username)
            elif packet_type == PacketType.SCHEDULE_BROADCAST.value:
                self.handle_schedule_broadcast(username, packet)
            elif packet_type == PacketType.UPDATE_STATUS.value:
                self.handle_status_update(username, packet)
            elif packet_type == PacketType.MATCHMAKE.value:
                self.handle_matchmake(username)
            elif packet_type == PacketType.FILE_START.value:
                self.handle_file_start(username, packet)
            elif packet_type == PacketType.FILE_CHUNK.value:
                self.handle_file_chunk(username, packet)
            elif packet_type == PacketType.FILE_END.value:
                self.handle_file_end(username, packet)
            elif packet_type == PacketType.IMAGE.value:
                self.handle_image_upload(username, packet)
            elif packet_type == PacketType.RECONNECT.value:
                self.handle_reconnect(username, packet)
            elif packet_type == PacketType.VOICE_START.value:
                self.handle_voice_start(username, packet)
            elif packet_type == PacketType.VOICE_STOP.value:
                self.handle_voice_stop(username, packet)
            elif packet_type == PacketType.VOICE_STATUS.value:
                self.handle_voice_status(username, packet)
            else:
                self.send_error(username, f"Unknown packet type: {packet_type}")
        except ValueError as exc:
            self.send_error(username, str(exc))
        except Exception as exc:
            self.logger.exception("Packet processing error for %s: %s", username, exc)
            self.send_error(username, "Internal server error")

    def handle_room_message(self, username: str, packet: Dict[str, Any]) -> None:
        room = self.user_rooms.get(username, "global")
        message = str(packet.get("message", "")).strip()
        if not message:
            raise ValueError("Cannot send an empty message.")
        if not self.room_manager.is_room_member(room, username):
            raise ValueError(f"You are not a member of room {room}.")
        self.database.save_message(username, message, "ROOM", room_name=room)
        self.broadcast_room_message(room, username, message)

    def handle_private_message(self, username: str, packet: Dict[str, Any]) -> None:
        target = str(packet.get("target", "")).strip()
        message = str(packet.get("message", "")).strip()
        if not target or not message:
            raise ValueError("Target and message are required for private messaging.")
        if self.database.find_user_id(target) is None:
            raise ValueError(f"Target user '{target}' does not exist.")
        self.database.save_message(username, message, "PRIVATE", target=target)
        if self.connections.send(target, PacketType.PRIVATE_MESSAGE, sender=username, target=target, message=message, timestamp=timestamp()):
            self.send_system(username, f"Message delivered to {target}.")
        else:
            self.send_system(username, f"{target} is offline. Message stored for later delivery.")

    def handle_create_room(self, username: str, packet: Dict[str, Any]) -> None:
        room_name = str(packet.get("room", "")).strip()
        if not room_name:
            raise ValueError("Room name is required.")
        visibility = str(packet.get("visibility", "public")).strip()
        max_capacity = int(packet.get("max_capacity", 50))
        invite_only = bool(packet.get("invite_only", False))
        password = packet.get("password")
        if not self.room_manager.create_room(room_name, username, visibility, max_capacity, invite_only, password):
            raise ValueError(f"Room '{room_name}' already exists.")
        self.send_system(username, f"Room '{room_name}' created.")
        self.handle_join_room(username, {"room": room_name, "password": password})

    def handle_join_room(self, username: str, packet: Dict[str, Any]) -> None:
        room_name = str(packet.get("room", "")).strip()
        password = packet.get("password")
        if not room_name:
            raise ValueError("Room name is required to join.")
        old_room = self.user_rooms.get(username, "global")
        room, error = self.room_manager.join_room(room_name, username, password=password)
        if error:
            raise ValueError(error)
        self.user_rooms[username] = room_name
        self.send_system(username, f"You joined room '{room_name}'.", room=room_name)
        if old_room != room_name:
            self.leave_room(username, old_room, silent=True)
        self.broadcast_system(f"{username} joined {room_name}.", room=room_name)
        self.send_room_history(username, room_name)

    def handle_leave_room(self, username: str, packet: Dict[str, Any]) -> None:
        current_room = self.user_rooms.get(username, "global")
        if current_room == "global":
            raise ValueError("Cannot leave the global room.")
        self.leave_room(username, current_room, silent=False)
        self.join_room(username, "global", announce=False)

    def handle_invite_user(self, username: str, packet: Dict[str, Any]) -> None:
        room_name = self.user_rooms.get(username, "global")
        target = str(packet.get("target", "")).strip()
        if not target:
            raise ValueError("Target username is required for invitation.")
        if not self.room_manager.is_owner(room_name, username):
            raise ValueError("Only the room owner may send invites.")
        self.room_manager.invite_user(room_name, target)
        self.database.invite_room_user(room_name, username, target)
        self.send_system(username, f"{target} has been invited to {room_name}.")
        self.connections.send(target, PacketType.SYSTEM, message=f"You have been invited to {room_name} by {username}.")

    def handle_kick_user(self, username: str, packet: Dict[str, Any]) -> None:
        room_name = self.user_rooms.get(username, "global")
        target = str(packet.get("target", "")).strip()
        if not target:
            raise ValueError("Target username is required to kick.")
        if not self.room_manager.is_owner(room_name, username):
            raise ValueError("Only the room owner may kick users.")
        self.room_manager.kick_user(room_name, target)
        self.send_system(username, f"{target} has been removed from {room_name}.")
        self.connections.send(target, PacketType.SYSTEM, message=f"You have been kicked from {room_name} by {username}.")
        if self.user_rooms.get(target) == room_name:
            self.join_room(target, "global", announce=False)

    def handle_delete_room(self, username: str, packet: Dict[str, Any]) -> None:
        room_name = str(packet.get("room", self.user_rooms.get(username, "global"))).strip()
        if not self.room_manager.is_owner(room_name, username):
            raise ValueError("Only the room owner can delete a room.")
        self.room_manager.delete_room(room_name)
        self.database.delete_room(room_name)
        self.send_system(username, f"Room '{room_name}' was deleted.")

    def handle_schedule_broadcast(self, username: str, packet: Dict[str, Any]) -> None:
        target_room = str(packet.get("target_room", "global")).strip()
        message = str(packet.get("message", "")).strip()
        send_time = str(packet.get("send_time", "")).strip()
        if not target_room or not message or not send_time:
            raise ValueError("target_room, message, and send_time are required.")
        try:
            datetime.strptime(send_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise ValueError("send_time must use format YYYY-MM-DD HH:MM:SS.")
        self.scheduler.schedule(target_room, message, send_time, username)
        self.send_system(username, f"Broadcast scheduled to {target_room} at {send_time}.")

    def handle_status_update(self, username: str, packet: Dict[str, Any]) -> None:
        status_value = str(packet.get("status", "ONLINE")).strip()
        try:
            status = UserStatus(status_value)
        except ValueError:
            status = UserStatus.ONLINE
        self.status_manager.set_status(username, status)
        self.send_system(username, f"Your status is now {status.value}.")

    def handle_matchmake(self, username: str) -> None:
        match_status = self.matchmaker.enqueue(username, self._finish_match)
        if match_status == "already_queued":
            self.send_system(username, "You are already in the matchmaking queue.")
            return
        if match_status == "queued":
            self.send_system(username, "You have entered the matchmaking queue. Waiting for a match...")
            return
        self.send_system(username, "Match found. Preparing room...")

    def _finish_match(self, participants: list[str]) -> None:
        room_name = f"match_{uuid.uuid4().hex[:8]}"
        owner = participants[0]
        if not self.room_manager.create_room(room_name, owner, visibility="private", max_capacity=10, invite_only=True):
            self.logger.error("Failed to create match room %s", room_name)
            return

        for participant in participants:
            self.room_manager.invite_user(room_name, participant)
            self.database.invite_room_user(room_name, owner, participant)

        for participant in participants:
            previous_room = self.user_rooms.get(participant, "global")
            if previous_room != room_name:
                self.leave_room(participant, previous_room, silent=True)
            room, error = self.room_manager.join_room(room_name, participant)
            if error:
                self.logger.warning("Failed to join %s to match room %s: %s", participant, room_name, error)
                continue
            self.user_rooms[participant] = room_name
            self.send_packet(
                participant,
                PacketType.MATCH_FOUND,
                room=room_name,
                participants=[p for p in participants if p != participant],
                message=f"Matched into room {room_name} with {', '.join([p for p in participants if p != participant])}.",
            )
            self.send_system(participant, f"Match found! You are now in {room_name}.", room=room_name)

    def send_room_history(self, username: str, room_name: str) -> None:
        history = self.database.fetch_room_messages(room_name)
        self.send_packet(username, PacketType.ROOM_HISTORY, room=room_name, history=history)

    def handle_image_upload(self, username: str, packet: Dict[str, Any]) -> None:
        filename = str(packet.get("filename", "")).strip()
        room = str(packet.get("room", self.user_rooms.get(username, "global"))).strip()
        target_user = packet.get("target_user")
        encoded_data = str(packet.get("data", ""))
        timestamp_value = timestamp()
        if not filename or not encoded_data:
            raise ValueError("Filename and image data are required.")
        raw_data = decode_bytes(encoded_data)
        valid, error = validate_image(filename, raw_data)
        if not valid:
            raise ValueError(error)
        if target_user:
            if self.database.find_user_id(target_user) is None:
                raise ValueError(f"Target user '{target_user}' does not exist.")
            file_path = save_image(username, target_user, filename, raw_data)
            transfer_id = generate_transfer_id(username, filename, timestamp_value)
            self.database.save_file_transfer(transfer_id, username, None, target_user, filename, len(raw_data), str(file_path), "IMAGE_PRIVATE", "COMPLETE")
            self.connections.send(target_user, PacketType.IMAGE, sender=username, target_user=target_user, filename=filename, filesize=len(raw_data), file_path=str(file_path), timestamp=timestamp_value)
            self.send_system(username, f"Sent image '{filename}' to {target_user}.")
            self.logger.info("Image transfer complete from %s to %s: %s", username, target_user, filename)
            return
        if not self.room_manager.is_room_member(room, username):
            raise ValueError(f"You are not a member of room {room}.")
        file_path = save_image(username, room, filename, raw_data)
        transfer_id = generate_transfer_id(username, filename, timestamp_value)
        self.database.save_file_transfer(transfer_id, username, room, None, filename, len(raw_data), str(file_path), "IMAGE_ROOM", "COMPLETE")
        members = self.room_manager.get_members(room)
        self.connections.broadcast(members, PacketType.IMAGE, sender=username, room=room, filename=filename, filesize=len(raw_data), file_path=str(file_path), timestamp=timestamp_value)
        self.send_system(username, f"Sent image '{filename}' to room {room}.")
        self.logger.info("Image broadcast complete from %s to room %s: %s", username, room, filename)

    def handle_file_start(self, username: str, packet: Dict[str, Any]) -> None:
        filename = str(packet.get("filename", "")).strip()
        filesize = int(packet.get("filesize", 0))
        target_room = packet.get("target_room")
        target_user = packet.get("target_user")
        transfer_id = str(packet.get("transfer_id", "")).strip()
        total_chunks = int(packet.get("total_chunks", 0))
        if not filename or filesize <= 0 or not transfer_id or total_chunks <= 0:
            raise ValueError("filename, filesize, transfer_id, and total_chunks are required for file transfer.")
        if filesize > 50 * 1024 * 1024:
            raise ValueError("File exceeds maximum allowed size of 50MB.")
        if target_user and self.database.find_user_id(target_user) is None:
            raise ValueError(f"Target user '{target_user}' does not exist.")
        metadata = {
            "sender": username,
            "filename": filename,
            "target_room": target_room or "",
            "target_user": target_user or "",
        }
        self.chunk_manager.begin_transfer(transfer_id, filename, total_chunks, metadata)
        self.database.save_file_transfer(transfer_id, username, target_room, target_user, filename, filesize, "", "FILE", "PENDING")
        self.send_system(username, f"Started file transfer '{filename}' ({filesize} bytes).")
        self.logger.info("Started file transfer %s by %s", transfer_id, username)

    def handle_file_chunk(self, username: str, packet: Dict[str, Any]) -> None:
        transfer_id = str(packet.get("transfer_id", "")).strip()
        chunk_index = int(packet.get("chunk_index", 0))
        encoded_data = str(packet.get("data", ""))
        if not transfer_id or chunk_index <= 0 or not encoded_data:
            raise ValueError("transfer_id, chunk_index and chunk data are required.")
        state = self.chunk_manager.get_state(transfer_id)
        if state is None:
            raise ValueError("Transfer does not exist or has been cancelled.")
        data = decode_bytes(encoded_data)
        self.chunk_manager.add_chunk(transfer_id, chunk_index, data)
        progress = len(state.received_chunks) / state.total_chunks * 100 if state.total_chunks else 0
        self.send_packet(username, PacketType.TRANSFER_PROGRESS, transfer_id=transfer_id, progress=int(progress), received=chunk_index)
        self.logger.debug("Received chunk %s for transfer %s", chunk_index, transfer_id)

    def handle_file_end(self, username: str, packet: Dict[str, Any]) -> None:
        transfer_id = str(packet.get("transfer_id", "")).strip()
        if not transfer_id:
            raise ValueError("transfer_id is required for file end.")
        state = self.chunk_manager.complete_transfer(transfer_id)
        if not state:
            raise ValueError("File transfer is not complete or missing chunks.")
        if state.missing_chunks():
            self.chunk_manager.cancel_transfer(transfer_id)
            raise ValueError(f"Missing chunks: {state.missing_chunks()}")
        file_bytes = b"".join(state.received_chunks[idx] for idx in range(1, state.total_chunks + 1))
        target_room = state.metadata.get("target_room") or None
        target_user = state.metadata.get("target_user") or None
        filename = state.filename
        file_path = self.storage_manager.room_upload_path(target_room if target_room else username, filename)
        self.storage_manager.save_file(file_path, file_bytes)
        self.database.save_file_transfer(transfer_id, username, target_room, target_user, filename, len(file_bytes), str(file_path), "FILE", "COMPLETE")
        if target_user:
            self.connections.send(target_user, PacketType.FILE, sender=username, target_user=target_user, filename=filename, filesize=len(file_bytes), file_path=str(file_path), timestamp=timestamp())
            self.send_system(username, f"File '{filename}' delivered to {target_user}.")
        else:
            room = target_room or self.user_rooms.get(username, "global")
            members = self.room_manager.get_members(room)
            self.connections.broadcast(members, PacketType.FILE, sender=username, room=room, filename=filename, filesize=len(file_bytes), file_path=str(file_path), timestamp=timestamp())
            self.send_system(username, f"File '{filename}' delivered to room {room}.")
        self.logger.info("Completed file transfer %s by %s", transfer_id, username)

    def handle_reconnect(self, username: str, packet: Dict[str, Any]) -> None:
        session_token = str(packet.get("session_token", "")).strip()
        if not session_token:
            raise ValueError("session_token is required for reconnect.")
        restored = self.session_manager.restore_session(session_token)
        if not restored:
            raise ValueError("Unable to restore session. Please log in again.")
        reconnect_username = restored["username"]
        reconnect_room = restored["room_name"]
        self.user_rooms[reconnect_username] = reconnect_room
        self.register_client(reconnect_username, skip_welcome=True)
        self.send_packet(reconnect_username, PacketType.SESSION_ACK, session_token=session_token, room=reconnect_room)
        self.send_system(reconnect_username, f"Reconnected to session and restored room {reconnect_room}.", room=reconnect_room)

    def send_online_users(self, username: Optional[str] = None) -> None:
        payload = {"online_users": self.connections.list_usernames()}
        if username:
            self.send_packet(username, PacketType.GET_ONLINE_USERS, **payload)
        else:
            self.connections.broadcast(self.connections.list_usernames(), PacketType.GET_ONLINE_USERS, **payload)

    def send_pending_friend_requests(self, username: str) -> None:
        pending = self.database.list_pending_friend_requests(username)
        for sender in pending:
            self.send_packet(
                username,
                PacketType.FRIEND_REQUEST,
                sender=sender,
                message=f"You have a pending friend request from {sender}.",
            )

    def broadcast_room_message(self, room: str, sender: str, message: str) -> None:
        members = self.room_manager.get_members(room)
        self.connections.broadcast(
            members,
            PacketType.MESSAGE,
            sender=sender,
            room=room,
            message=message,
            timestamp=timestamp(),
        )

    def broadcast_system(self, message: str, room: str = "global") -> None:
        members = self.room_manager.get_members(room)
        self.connections.broadcast(
            members,
            PacketType.SYSTEM,
            room=room,
            message=message,
            timestamp=timestamp(),
        )

    def send_packet(self, username: str, packet_type: PacketType, **fields: object) -> None:
        if not self.connections.send(username, packet_type, timestamp=timestamp(), sender="server", **fields):
            self.logger.debug("Failed to send packet to %s", username)

    def send_system(self, username: str, message: str, room: str = "global") -> None:
        self.send_packet(username, PacketType.SYSTEM, room=room, message=message)

    def send_error(self, username: str, message: str) -> None:
        self.send_packet(username, PacketType.ERROR, message=message)

    def leave_room(self, username: str, room_name: str, silent: bool = False) -> None:
        if not self.room_manager.is_room_member(room_name, username):
            return
        self.room_manager.leave_room(room_name, username)
        self.database.remove_room_member(room_name, username)
        if self.user_rooms.get(username) == room_name:
            self.user_rooms[username] = "global"
        if not silent:
            self.send_system(username, f"You left {room_name}.", room=room_name)
            self.broadcast_system(f"{username} left {room_name}.", room=room_name)

    def join_room(self, username: str, room_name: str, password: Optional[str] = None, announce: bool = True) -> None:
        room, error = self.room_manager.join_room(room_name, username, password=password)
        if error:
            raise ValueError(error)
        self.user_rooms[username] = room_name
        if announce:
            self.broadcast_system(f"{username} joined {room_name}.", room=room_name)

    def dispatch_scheduled_broadcast(self, room_name: str, message: str) -> None:
        self.database.save_message("system", message, "SYSTEM", room_name=room_name)
        self.broadcast_system(message, room=room_name)

    def unregister_client(self, username: str) -> None:
        with self.lock:
            self.connections.remove(username)
            self.matchmaker.leave_queue(username)
            current_room = self.user_rooms.get(username, "global")
            self.room_manager.leave_room(current_room, username)
            self.database.remove_room_member(current_room, username)
            self.status_manager.remove(username)
            self.session_manager.end_session(username)
            self.user_rooms.pop(username, None)
            voice_room = self.voice_room_manager.user_voice_room(username)
            if voice_room:
                self.voice_room_manager.remove_from_room(voice_room, username)
            self.broadcast_system(f"{username} disconnected.", room=current_room)
            self.send_online_users()

    def handle_voice_start(self, username: str, packet: Dict[str, Any]) -> None:
        room = str(packet.get("room", self.user_rooms.get(username, "global"))).strip()
        udp_port = int(packet.get("udp_port", 0))
        if not room or udp_port <= 0:
            raise ValueError("room and udp_port are required for VOICE_START.")
        if not self.room_manager.is_room_member(room, username):
            raise ValueError(f"You are not a member of room {room}.")
        old_voice_room = self.voice_room_manager.user_voice_room(username)
        if old_voice_room and old_voice_room != room:
            self.voice_room_manager.remove_from_room(old_voice_room, username)
            self.broadcast_system(f"{username} left voice in {old_voice_room}.", room=old_voice_room)
        self.voice_room_manager.add_to_room(room, username, udp_port)
        self.send_system(username, f"Joined voice in room '{room}'.", room=room)
        self.broadcast_system(f"{username} joined voice.", room=room)
        self.logger.info("%s started voice in %s (UDP port %d)", username, room, udp_port)

    def handle_voice_stop(self, username: str, packet: Dict[str, Any]) -> None:
        room = str(packet.get("room", "")).strip()
        if not room:
            room = self.voice_room_manager.user_voice_room(username)
        if room:
            self.voice_room_manager.remove_from_room(room, username)
            self.send_system(username, f"Left voice in room '{room}'.", room=room)
            self.broadcast_system(f"{username} left voice.", room=room)
            self.logger.info("%s stopped voice in %s", username, room)

    def handle_voice_status(self, username: str, packet: Dict[str, Any]) -> None:
        room = str(packet.get("room", "")).strip()
        status = str(packet.get("status", "")).strip()
        if not room or not status:
            raise ValueError("room and status are required for VOICE_STATUS.")
        voice_room = self.voice_room_manager.get_room(room)
        if not voice_room:
            raise ValueError(f"No active voice session in {room}.")
        if status == "muted":
            voice_room.set_muted(username, True)
            self.broadcast_system(f"{username} is muted.", room=room)
        elif status == "unmuted":
            voice_room.set_muted(username, False)
            self.broadcast_system(f"{username} is unmuted.", room=room)
        elif status == "speaking":
            voice_room.set_speaking(username, True)
        elif status == "idle":
            voice_room.set_speaking(username, False)

