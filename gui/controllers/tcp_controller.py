"""TCP controller for realtime communication with Convox server."""

import socket
from typing import Any, Dict, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal, QMutex

from protocol.packet import PacketType, build_packet, receive_packet
from gui.controllers.event_dispatcher import get_dispatcher
from utils.logger import get_logger


class TCPWorker(QObject):
    """Worker thread for TCP communication."""

    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, host: str, port: int):
        super().__init__()
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.logger = get_logger("TCPWorker")
        self.dispatcher = get_dispatcher()
        self.send_mutex = QMutex()
        self.username: Optional[str] = None
        self.session_token: Optional[str] = None

    def connect_to_server(self) -> bool:
        """Establish TCP connection to server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.socket.connect((self.host, self.port))
            self.logger.info("Connected to server at %s:%s", self.host, self.port)
            self.dispatcher.connected.emit()
            return True
        except OSError as exc:
            error_msg = f"Connection failed: {exc}"
            self.logger.error(error_msg)
            self.dispatcher.connection_error.emit(error_msg)
            return False

    def login(self, username: str, password: str = "") -> None:
        """Send login packet."""
        self.username = username
        packet = build_packet(
            PacketType.LOGIN,
            sender=username,
            username=username,
            password=password,
        )
        self.send_raw(packet)
        self.logger.info("Sent LOGIN for %s", username)

    def register_account(self, username: str, password: str) -> None:
        """Send registration packet."""
        self.username = username
        packet = build_packet(
            PacketType.REGISTER,
            sender=username,
            username=username,
            password=password,
        )
        self.send_raw(packet)
        self.logger.info("Sent REGISTER for %s", username)

    def reconnect(self, session_token: str) -> None:
        """Send reconnect packet."""
        self.session_token = session_token
        packet = build_packet(PacketType.RECONNECT, session_token=session_token)
        self.send_raw(packet)
        self.logger.info("Sent RECONNECT")

    def send_message(self, room: str, message: str) -> None:
        """Send chat message."""
        packet = build_packet(PacketType.MESSAGE, room=room, message=message)
        self.send_raw(packet)

    def send_private_message(self, target: str, message: str) -> None:
        """Send private message."""
        packet = build_packet(PacketType.PRIVATE_MESSAGE, target=target, message=message)
        self.send_raw(packet)

    def join_room(self, room: str, password: Optional[str] = None) -> None:
        """Join a room."""
        packet = build_packet(PacketType.JOIN_ROOM, room=room, password=password or "")
        self.send_raw(packet)

    def leave_room(self, room: str) -> None:
        """Leave a room."""
        packet = build_packet(PacketType.LEAVE_ROOM, room=room)
        self.send_raw(packet)

    def create_room(self, room: str, visibility: str = "public", max_capacity: int = 50) -> None:
        """Create a room."""
        packet = build_packet(
            PacketType.CREATE_ROOM,
            room=room,
            visibility=visibility,
            max_capacity=max_capacity,
        )
        self.send_raw(packet)

    def delete_room(self, room: str) -> None:
        """Delete a room."""
        packet = build_packet(PacketType.DELETE_ROOM, room=room)
        self.send_raw(packet)

    def add_friend(self, friend: str) -> None:
        """Send friend request."""
        packet = build_packet(PacketType.ADD_FRIEND, friend=friend)
        self.send_raw(packet)

    def accept_friend(self, friend: str) -> None:
        """Accept friend request."""
        packet = build_packet(PacketType.ACCEPT_FRIEND, friend=friend)
        self.send_raw(packet)

    def reject_friend(self, friend: str) -> None:
        """Reject friend request."""
        packet = build_packet(PacketType.REJECT_FRIEND, friend=friend)
        self.send_raw(packet)

    def remove_friend(self, friend: str) -> None:
        """Remove friend."""
        packet = build_packet(PacketType.REMOVE_FRIEND, friend=friend)
        self.send_raw(packet)

    def get_friends(self) -> None:
        """Request friend list."""
        packet = build_packet(PacketType.GET_FRIENDS)
        self.send_raw(packet)

    def get_online_users(self) -> None:
        """Request online user list."""
        packet = build_packet(PacketType.GET_ONLINE_USERS)
        self.send_raw(packet)

    def update_status(self, status: str) -> None:
        """Update presence status."""
        packet = build_packet(PacketType.UPDATE_STATUS, status=status)
        self.send_raw(packet)

    def invite_user(self, target: str) -> None:
        """Invite user to room."""
        packet = build_packet(PacketType.INVITE_USER, target=target)
        self.send_raw(packet)

    def kick_user(self, target: str) -> None:
        """Kick user from room."""
        packet = build_packet(PacketType.KICK_USER, target=target)
        self.send_raw(packet)

    def send_voice_start(self, room: str, udp_port: int) -> None:
        """Start voice session."""
        packet = build_packet(PacketType.VOICE_START, room=room, udp_port=udp_port)
        self.send_raw(packet)

    def send_voice_stop(self, room: str) -> None:
        """Stop voice session."""
        packet = build_packet(PacketType.VOICE_STOP, room=room)
        self.send_raw(packet)

    def send_voice_status(self, room: str, status: str) -> None:
        """Update voice status."""
        packet = build_packet(PacketType.VOICE_STATUS, room=room, status=status)
        self.send_raw(packet)

    def send_raw(self, packet: bytes) -> None:
        """Send raw packet data."""
        if not self.socket:
            return
        try:
            self.send_mutex.lock()
            try:
                self.socket.sendall(packet)
            finally:
                self.send_mutex.unlock()
        except OSError as exc:
            self.logger.exception("Send error: %s", exc)
            self.dispatcher.error.emit(str(exc))

    def run(self) -> None:
        """Main receive loop (runs in worker thread)."""
        if not self.connect_to_server():
            self.finished.emit()
            return

        self.running = True
        while self.running:
            try:
                packet_data = receive_packet(self.socket)
                if packet_data is None:
                    self.logger.info("Server closed connection")
                    break
                self.handle_packet(packet_data)
            except OSError as exc:
                if self.running:
                    self.logger.error("Receive error: %s", exc)
                    self.dispatcher.connection_error.emit(str(exc))
                break
            except Exception as exc:
                self.logger.exception("Packet handling error: %s", exc)
                self.dispatcher.error.emit(str(exc))

        self.disconnect()
        self.finished.emit()

    def handle_packet(self, packet: Dict[str, Any]) -> None:
        """Route incoming packet to dispatcher."""
        packet_type = packet.get("type")

        try:
            if packet_type == PacketType.AUTH_SUCCESS.value:
                self.session_token = packet.get("session_token") or self.session_token
                self.username = packet.get("username") or self.username
                room = packet.get("room", "global")
                # AUTH_SUCCESS arrives both for registration (no token)
                # and for login. Only emit login_success when we have a
                # session token so the GUI can move on to the dashboard;
                # registration acks are surfaced via the system message.
                if self.session_token:
                    self.dispatcher.login_success.emit(self.username or "")
                    self.dispatcher.session_restored.emit(
                        self.username or "", room or "global"
                    )
                else:
                    self.dispatcher.register_success.emit(self.username or "")
                    self.dispatcher.system_message.emit(
                        "auth",
                        packet.get("message", "Account created. You may now sign in."),
                    )

            elif packet_type == PacketType.AUTH_FAILED.value:
                message = packet.get("message", "Authentication failed.")
                self.dispatcher.login_failed.emit(message)

            elif packet_type == PacketType.SESSION_ACK.value:
                self.session_token = packet.get("session_token") or self.session_token
                self.username = packet.get("username") or self.username
                room = packet.get("room", "global")
                # Always raise both login_success and session_restored so
                # consumers can pick the variant they need; reconnect users
                # will have already supplied a session token, while fresh
                # logins start with self.session_token == None.
                self.dispatcher.login_success.emit(self.username or "")
                self.dispatcher.session_restored.emit(self.username or "", room or "global")

            elif packet_type == PacketType.MESSAGE.value:
                room = packet.get("room", "global")
                sender = packet.get("sender", "unknown")
                message = packet.get("message", "")
                timestamp = packet.get("timestamp", "")
                self.dispatcher.message_received.emit(room, sender, message, timestamp)

            elif packet_type == PacketType.PRIVATE_MESSAGE.value:
                sender = packet.get("sender", "unknown")
                message = packet.get("message", "")
                timestamp = packet.get("timestamp", "")
                self.dispatcher.private_message_received.emit(sender, message, timestamp)

            elif packet_type == PacketType.SYSTEM.value:
                room = packet.get("room", "global")
                message = packet.get("message", "")
                self.dispatcher.system_message.emit(room, message)

            elif packet_type == PacketType.FRIEND_REQUEST.value:
                sender = packet.get("sender", "unknown")
                self.dispatcher.friend_request_received.emit(sender)

            elif packet_type == PacketType.FRIEND_LIST.value:
                friends = packet.get("friends", [])
                self.dispatcher.friend_list_updated.emit(friends)

            elif packet_type == PacketType.GET_ONLINE_USERS.value:
                users = packet.get("online_users", [])
                self.dispatcher.online_users_updated.emit(users)

            elif packet_type == PacketType.STATUS_UPDATE.value:
                user = packet.get("user", "unknown")
                status = packet.get("status", "ONLINE")
                self.dispatcher.user_status_changed.emit(user, status)

            elif packet_type == PacketType.IMAGE.value:
                room = packet.get("room") or packet.get("sender", "direct")
                filename = packet.get("filename", "unknown")
                file_path = packet.get("file_path", "")
                self.dispatcher.image_received.emit(room, filename, file_path)

            elif packet_type == PacketType.FILE.value:
                room = packet.get("room") or packet.get("sender", "direct")
                filename = packet.get("filename", "unknown")
                file_path = packet.get("file_path", "")
                transfer_id = packet.get("transfer_id", filename)
                filesize = int(packet.get("filesize") or 0)
                self.dispatcher.file_transfer_complete.emit(transfer_id)
                self.dispatcher.image_received.emit(room, filename, file_path)
                # Also surface as a transfer-start so panels not aware of
                # the upload still see it appear.
                self.dispatcher.file_transfer_started.emit(transfer_id, filename, filesize)

            elif packet_type == PacketType.TRANSFER_PROGRESS.value:
                transfer_id = packet.get("transfer_id", "unknown")
                progress = packet.get("progress", 0)
                self.dispatcher.file_transfer_progress.emit(transfer_id, progress)

            elif packet_type == PacketType.ERROR.value:
                message = packet.get("message", "Unknown error")
                self.dispatcher.error.emit(message)

        except Exception as exc:
            self.logger.exception("Packet handling failed: %s", exc)

    def disconnect(self) -> None:
        """Close connection."""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except OSError:
                pass
        self.logger.info("Disconnected from server")
        self.dispatcher.disconnected.emit()


class TCPController(QObject):
    """Main TCP controller managing worker thread."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9000):
        super().__init__()
        self.host = host
        self.port = port
        self.worker: Optional[TCPWorker] = None
        self.thread: Optional[QThread] = None
        self.logger = get_logger("TCPController")

    def start(self) -> None:
        """Start TCP worker thread."""
        if self.thread:
            return

        self.thread = QThread()
        self.worker = TCPWorker(self.host, self.port)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()
        self.logger.info("TCP worker thread started")

    def stop(self) -> None:
        """Stop TCP worker thread."""
        worker = self.worker
        thread = self.thread
        if worker:
            worker.running = False
            try:
                if worker.socket:
                    worker.socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                if worker.socket:
                    worker.socket.close()
            except OSError:
                pass
        if thread:
            thread.quit()
            thread.wait(2000)
        self.thread = None
        self.worker = None
        self.logger.info("TCP worker thread stopped")

    def login(self, username: str, password: str = "") -> None:
        """Queue login request."""
        if self.worker:
            self.worker.login(username, password)

    def register_account(self, username: str, password: str) -> None:
        """Queue registration request."""
        if self.worker:
            self.worker.register_account(username, password)

    def reconnect(self, session_token: str) -> None:
        """Queue reconnect request."""
        if self.worker:
            self.worker.reconnect(session_token)

    def send_message(self, room: str, message: str) -> None:
        """Queue message send."""
        if self.worker:
            self.worker.send_message(room, message)

    def send_private_message(self, target: str, message: str) -> None:
        """Queue private message send."""
        if self.worker:
            self.worker.send_private_message(target, message)

    def join_room(self, room: str, password: Optional[str] = None) -> None:
        """Queue room join."""
        if self.worker:
            self.worker.join_room(room, password)

    def leave_room(self, room: str) -> None:
        """Queue room leave."""
        if self.worker:
            self.worker.leave_room(room)

    def create_room(self, room: str, visibility: str = "public", max_capacity: int = 50) -> None:
        """Queue room creation."""
        if self.worker:
            self.worker.create_room(room, visibility, max_capacity)

    def delete_room(self, room: str) -> None:
        """Queue room deletion."""
        if self.worker:
            self.worker.delete_room(room)

    def add_friend(self, friend: str) -> None:
        """Queue friend request."""
        if self.worker:
            self.worker.add_friend(friend)

    def accept_friend(self, friend: str) -> None:
        """Queue friend accept."""
        if self.worker:
            self.worker.accept_friend(friend)

    def reject_friend(self, friend: str) -> None:
        """Queue friend reject."""
        if self.worker:
            self.worker.reject_friend(friend)

    def remove_friend(self, friend: str) -> None:
        """Queue friend remove."""
        if self.worker:
            self.worker.remove_friend(friend)

    def get_friends(self) -> None:
        """Queue get friends."""
        if self.worker:
            self.worker.get_friends()

    def get_online_users(self) -> None:
        """Queue get online users."""
        if self.worker:
            self.worker.get_online_users()

    def update_status(self, status: str) -> None:
        """Queue status update."""
        if self.worker:
            self.worker.update_status(status)

    def invite_user(self, target: str) -> None:
        """Queue user invite."""
        if self.worker:
            self.worker.invite_user(target)

    def kick_user(self, target: str) -> None:
        """Queue user kick."""
        if self.worker:
            self.worker.kick_user(target)

    def send_voice_start(self, room: str, udp_port: int) -> None:
        """Queue voice start."""
        if self.worker:
            self.worker.send_voice_start(room, udp_port)

    def send_voice_stop(self, room: str) -> None:
        """Queue voice stop."""
        if self.worker:
            self.worker.send_voice_stop(room)

    def send_voice_status(self, room: str, status: str) -> None:
        """Queue voice status update."""
        if self.worker:
            self.worker.send_voice_status(room, status)
