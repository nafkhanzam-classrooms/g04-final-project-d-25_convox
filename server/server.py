import socket
import threading

from protocol.packet import PacketType, build_packet, receive_packet
from server.service import ConvoxService
from .config import MAX_CONNECTIONS, SERVER_HOST, SERVER_PORT
from utils.logger import get_logger


class ConvoxServer:
    """Convox TCP server.

    Handles the initial handshake (REGISTER / LOGIN / RECONNECT), then
    delegates every subsequent packet to ``ConvoxService``.
    """

    def __init__(self) -> None:
        self.host = SERVER_HOST
        self.port = SERVER_PORT
        self.logger = get_logger("ConvoxServer")
        self.service = ConvoxService()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def start(self) -> None:
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(MAX_CONNECTIONS)
        self.logger.info("Convox server listening on %s:%s", self.host, self.port)

        try:
            while True:
                conn, address = self.server_socket.accept()
                self.logger.info("New connection from %s:%s", *address)
                thread = threading.Thread(target=self.handle_client, args=(conn, address), daemon=True)
                thread.start()
        except KeyboardInterrupt:
            self.logger.info("Shutting down Convox server")
        finally:
            self.server_socket.close()

    # --------------------------------------------------------- client lifecycle
    def handle_client(self, conn: socket.socket, address: tuple[str, int]) -> None:
        username: str | None = None
        try:
            username = self._authenticate(conn, address)
            if not username:
                conn.close()
                return

            while True:
                packet = receive_packet(conn)
                if packet is None:
                    break
                self.service.route_packet(packet, username)
        except Exception as exc:
            self.logger.exception("Error handling client %s: %s", address, exc)
        finally:
            if username:
                self.service.unregister_client(username)
            try:
                conn.close()
            except OSError:
                pass

    # ---------------------------------------------------------------- handshake
    def _authenticate(self, conn: socket.socket, address: tuple[str, int]) -> str | None:
        """Run the auth/reconnect handshake.

        The first packet must be REGISTER, LOGIN or RECONNECT. We allow
        a small loop so a failed REGISTER/LOGIN can be retried over the
        same socket without forcing the GUI to reopen the connection.
        """
        for _ in range(5):
            packet = receive_packet(conn)
            if packet is None:
                return None
            packet_type = packet.get("type")

            if packet_type == PacketType.REGISTER.value:
                if self._handle_register(conn, packet, address):
                    continue  # registration succeeded, wait for LOGIN next
                continue  # failure already reported, allow retry

            if packet_type == PacketType.LOGIN.value:
                username = self._handle_login(conn, packet, address)
                if username:
                    return username
                continue

            if packet_type == PacketType.RECONNECT.value:
                username = self._handle_reconnect(conn, packet, address)
                if username:
                    return username
                continue

            self._send_auth_failed(conn, "First packet must be REGISTER, LOGIN or RECONNECT.")
            return None

        self._send_auth_failed(conn, "Too many failed authentication attempts.")
        return None

    def _handle_register(self, conn: socket.socket, packet: dict, address: tuple[str, int]) -> bool:
        username = str(packet.get("username") or packet.get("sender") or "").strip()
        password = str(packet.get("password") or "")
        try:
            registered = self.service.auth_service.register(username, password)
        except ValueError as exc:
            self._send_auth_failed(conn, str(exc))
            self.logger.info("Registration rejected for %s@%s:%s: %s", username, *address, exc)
            return False
        self.logger.info("User registered: %s (%s:%s)", registered, *address)
        self._send_packet(conn, PacketType.AUTH_SUCCESS, username=registered, message="Account created. You may now sign in.")
        return True

    def _handle_login(self, conn: socket.socket, packet: dict, address: tuple[str, int]) -> str | None:
        username = str(packet.get("username") or packet.get("sender") or "").strip()
        password = str(packet.get("password") or "")
        try:
            authenticated = self.service.auth_service.authenticate(username, password)
        except ValueError as exc:
            self._send_auth_failed(conn, str(exc))
            self.logger.info("Login failed for %s@%s:%s: %s", username, *address, exc)
            return None

        if self.service.connections.get(authenticated):
            self._send_auth_failed(conn, "This account is already connected from another client.")
            return None

        self.service.connections.add(authenticated, conn)
        self.service.user_rooms[authenticated] = "global"
        room = "global"
        session_token = self.service.session_manager.create_session(authenticated, room)

        # Send the auth response first so the client always sees the
        # AUTH_SUCCESS / SESSION_ACK pair before any room-side traffic.
        self._send_packet(
            conn,
            PacketType.AUTH_SUCCESS,
            sender="server",
            username=authenticated,
            session_token=session_token,
            room=room,
            message=f"Welcome back, {authenticated}.",
        )
        self._send_packet(
            conn,
            PacketType.SESSION_ACK,
            sender="server",
            username=authenticated,
            session_token=session_token,
            room=room,
        )

        # Now register the client which fires welcome / presence packets.
        self.service.register_client(authenticated)
        self.logger.info("User logged in: %s (%s:%s)", authenticated, *address)
        return authenticated

    def _handle_reconnect(self, conn: socket.socket, packet: dict, address: tuple[str, int]) -> str | None:
        session_token = str(packet.get("session_token", "")).strip()
        restored = self.service.session_manager.restore_session(session_token)
        if not restored:
            self._send_auth_failed(conn, "Unable to restore session. Please log in again.")
            return None

        username = restored["username"]
        room_name = restored["room_name"]
        if self.service.connections.get(username):
            self._send_auth_failed(conn, "This account is already connected from another client.")
            return None

        self.service.user_rooms[username] = room_name
        self.service.connections.add(username, conn)
        # Send auth response first so the GUI sees AUTH_SUCCESS + SESSION_ACK
        # before any room/system traffic that register_client may emit.
        self._send_packet(
            conn,
            PacketType.AUTH_SUCCESS,
            sender="server",
            username=username,
            session_token=session_token,
            room=room_name,
            message=f"Reconnected as {username}.",
        )
        self._send_packet(
            conn,
            PacketType.SESSION_ACK,
            sender="server",
            username=username,
            session_token=session_token,
            room=room_name,
        )
        self.service.register_client(username, skip_welcome=True)
        self.logger.info("User reconnected: %s (%s:%s)", username, *address)
        return username

    # ---------------------------------------------------------------- helpers
    def _send_packet(self, conn: socket.socket, packet_type: PacketType, **fields: object) -> None:
        try:
            conn.sendall(build_packet(packet_type, **fields))
        except OSError:
            pass

    def _send_auth_failed(self, conn: socket.socket, message: str) -> None:
        self._send_packet(conn, PacketType.AUTH_FAILED, message=message)

    def send_error(self, conn: socket.socket, message: str) -> None:
        self._send_packet(conn, PacketType.ERROR, message=message)
