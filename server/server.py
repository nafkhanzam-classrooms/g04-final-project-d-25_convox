import socket
import threading

from protocol.packet import PacketType, build_packet, receive_packet
from server.service import ConvoxService
from .config import MAX_CONNECTIONS, SERVER_HOST, SERVER_PORT
from utils.logger import get_logger


class ConvoxServer:
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

    def handle_client(self, conn: socket.socket, address: tuple[str, int]) -> None:
        username = None
        try:
            packet = receive_packet(conn)
            if packet is None:
                conn.close()
                return
            packet_type = packet.get("type")
            if packet_type == PacketType.RECONNECT.value:
                session_token = str(packet.get("session_token", "")).strip()
                restored = self.service.session_manager.restore_session(session_token)
                if not restored:
                    self.send_error(conn, "Unable to restore session. Please log in again.")
                    conn.close()
                    return
                username = restored["username"]
                room_name = restored["room_name"]
                if self.service.connections.get(username):
                    self.send_error(conn, "Username already connected.")
                    conn.close()
                    return
                self.service.user_rooms[username] = room_name
                self.service.connections.add(username, conn)
                self.service.register_client(username, skip_welcome=True)
                self.service.send_packet(username, PacketType.SESSION_ACK, username=username, session_token=session_token, room=room_name)
                self.logger.info("User reconnected: %s (%s:%s)", username, *address)
            elif packet_type == PacketType.LOGIN.value:
                username = str(packet.get("sender", "")).strip()
                if not username:
                    self.send_error(conn, "Username is required for login.")
                    conn.close()
                    return
                if self.service.connections.get(username):
                    self.send_error(conn, "Username already connected.")
                    conn.close()
                    return
                self.service.connections.add(username, conn)
                self.service.register_client(username)
                session_token = self.service.session_manager.create_session(username, self.service.user_rooms[username])
                self.service.send_packet(username, PacketType.SESSION_ACK, username=username, session_token=session_token, room=self.service.user_rooms[username])
                self.logger.info("User logged in: %s (%s:%s)", username, *address)
            else:
                self.send_error(conn, "First packet must be LOGIN or RECONNECT.")
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
            conn.close()

    def send_error(self, conn: socket.socket, message: str) -> None:
        packet = build_packet(PacketType.ERROR, message=message)
        conn.sendall(packet)
