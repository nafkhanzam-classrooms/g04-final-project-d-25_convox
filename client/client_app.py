import socket
import threading
import uuid
from pathlib import Path
from typing import Optional

from client.config import SERVER_HOST, SERVER_PORT
from protocol.packet import PacketType, build_packet, receive_packet
from utils.logger import get_logger


class ConvoxClient:
    def __init__(self):
        self.server_host = SERVER_HOST
        self.server_port = SERVER_PORT
        self.username: Optional[str] = None
        self.session_token: Optional[str] = None
        self.current_room: str = "global"
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.receiver_thread: Optional[threading.Thread] = None
        self.logger = get_logger("ConvoxClient")
        self.running = False

    def connect(self) -> None:
        self.socket.connect((self.server_host, self.server_port))
        self.logger.info("Connected to server at %s:%s", self.server_host, self.server_port)

    def login(self) -> None:
        while not self.username:
            candidate = input("Enter username: ").strip()
            if candidate:
                self.username = candidate
        packet = build_packet(PacketType.LOGIN, sender=self.username)
        self.socket.sendall(packet)
        self.running = True
        self.receiver_thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.receiver_thread.start()

    def receive_loop(self) -> None:
        while self.running:
            packet = receive_packet(self.socket)
            if packet is None:
                self.logger.info("Server closed connection")
                break
            self.display_packet(packet)
        self.running = False

    def display_packet(self, packet: dict) -> None:
        packet_type = packet.get("type")
        sender = packet.get("sender", "server")
        room = packet.get("room", "global")
        message = packet.get("message", "")
        timestamp = packet.get("timestamp", "")

        if packet_type == PacketType.SESSION_ACK.value:
            self.session_token = packet.get("session_token")
            self.username = packet.get("username") or self.username
            self.current_room = packet.get("room", "global")
            print(f"[SESSION] Session restored: {self.session_token[:16]}...")
        elif packet_type == PacketType.MESSAGE.value:
            print(f"[{timestamp}] [{room}] {sender}: {message}")
        elif packet_type == PacketType.PRIVATE_MESSAGE.value:
            print(f"[{timestamp}] [PRIVATE] {sender}: {message}")
        elif packet_type == PacketType.IMAGE.value:
            filename = packet.get("filename", "unknown")
            filesize = packet.get("filesize", 0)
            print(f"[{timestamp}] [IMAGE] {sender} sent: {filename} ({filesize} bytes)")
        elif packet_type == PacketType.FILE.value:
            filename = packet.get("filename", "unknown")
            filesize = packet.get("filesize", 0)
            print(f"[{timestamp}] [FILE] {sender} sent: {filename} ({filesize} bytes)")
        elif packet_type == PacketType.MATCH_FOUND.value:
            room = packet.get("room", "unknown")
            participants = packet.get("participants", [])
            print(f"[{timestamp}] [MATCH] Join room {room} with {', '.join(participants)}")
        elif packet_type == PacketType.TRANSFER_PROGRESS.value:
            transfer_id = packet.get("transfer_id", "unknown")
            progress = packet.get("progress", 0)
            print(f"[PROGRESS] Transfer {transfer_id[:16]}...: {progress}%")
        elif packet_type == PacketType.FRIEND_REQUEST.value:
            request_sender = packet.get("sender", "unknown")
            print(f"[{timestamp}] [FRIEND REQUEST] {request_sender} sent you a friend request.")
        elif packet_type == PacketType.FRIEND_LIST.value:
            friends = packet.get("friends", [])
            print("Friend list:")
            for friend in friends:
                print(f"  {friend.get('username')} ({friend.get('status')})")
        elif packet_type == PacketType.STATUS_UPDATE.value:
            user = packet.get("user", "unknown")
            status = packet.get("status", "UNKNOWN")
            print(f"[{timestamp}] [STATUS] {user} is now {status}.")
        elif packet_type == PacketType.ROOM_HISTORY.value:
            history = packet.get("history", [])
            print(f"[{timestamp}] [HISTORY] Last messages in {room}:")
            for item in history:
                print(f"  [{item.get('timestamp')}] {item.get('sender')}: {item.get('content')}")
        elif packet_type == PacketType.SYSTEM.value:
            print(f"[{timestamp}] [SYSTEM] {message}")
        elif packet_type == PacketType.ERROR.value:
            print(f"[ERROR] {message}")
        elif packet_type == PacketType.GET_ONLINE_USERS.value:
            users = packet.get("online_users", [])
            print(f"Online users: {', '.join(users)}")
        else:
            print(f"[RECEIVED] {packet}")

    def send_packet(self, packet_type: PacketType, **fields) -> None:
        packet = build_packet(packet_type, sender=self.username, **fields)
        self.socket.sendall(packet)

    def run(self) -> None:
        try:
            self.connect()
            self.login()
            print("Convox Terminal Client. Type /help for commands.")
            while self.running:
                payload = input().strip()
                if not payload:
                    continue
                if payload.startswith("/"):
                    self.handle_command(payload)
                else:
                    self.send_packet(PacketType.MESSAGE, room=self.current_room, message=payload)
        except KeyboardInterrupt:
            print("\nExiting client")
        finally:
            self.running = False
            self.socket.close()

    def handle_command(self, payload: str) -> None:
        parts = payload.split(maxsplit=2)
        command = parts[0].lower()

        if command == "/help":
            self.print_help()
        elif command == "/online":
            self.send_packet(PacketType.GET_ONLINE_USERS)
        elif command == "/join" and len(parts) >= 2:
            self.current_room = parts[1]
            self.send_packet(PacketType.JOIN_ROOM, room=parts[1])
        elif command == "/create" and len(parts) >= 2:
            self.send_packet(PacketType.CREATE_ROOM, room=parts[1])
        elif command == "/leave":
            self.send_packet(PacketType.LEAVE_ROOM, room=self.current_room)
        elif command == "/invite" and len(parts) >= 2:
            self.send_packet(PacketType.INVITE_USER, target=parts[1])
        elif command == "/kick" and len(parts) >= 2:
            self.send_packet(PacketType.KICK_USER, target=parts[1])
        elif command == "/delete" and len(parts) >= 2:
            self.send_packet(PacketType.DELETE_ROOM, room=parts[1])
        elif command == "/matchmake":
            self.send_packet(PacketType.MATCHMAKE)
        elif command == "/friend" and len(parts) >= 2:
            self.send_packet(PacketType.ADD_FRIEND, friend=parts[1])
        elif command == "/accept" and len(parts) >= 2:
            self.send_packet(PacketType.ACCEPT_FRIEND, friend=parts[1])
        elif command == "/reject" and len(parts) >= 2:
            self.send_packet(PacketType.REJECT_FRIEND, friend=parts[1])
        elif command == "/remove" and len(parts) >= 2:
            self.send_packet(PacketType.REMOVE_FRIEND, friend=parts[1])
        elif command == "/friends":
            self.send_packet(PacketType.GET_FRIENDS)
        elif command == "/msg" and len(parts) == 3:
            target, message = parts[1], parts[2]
            self.send_packet(PacketType.PRIVATE_MESSAGE, target=target, message=message)
        elif command == "/status" and len(parts) >= 2:
            self.send_packet(PacketType.UPDATE_STATUS, status=parts[1].upper())
        elif command == "/sendimage" and len(parts) >= 2:
            self.send_image(parts[1])
        elif command == "/sendfile" and len(parts) >= 2:
            self.send_file(parts[1])
        elif command == "/reconnect" and self.session_token:
            self.send_packet(PacketType.RECONNECT, session_token=self.session_token)
        elif command == "/quit":
            self.running = False
            self.socket.close()
            print("Disconnected from Convox")
        else:
            print("Unknown command. Type /help for available commands.")

    def send_image(self, image_path: str) -> None:
        path = Path(image_path)
        if not path.exists():
            print(f"Image file not found: {image_path}")
            return
        try:
            data = path.read_bytes()
            import base64
            encoded = base64.b64encode(data).decode("ascii")
            self.send_packet(PacketType.IMAGE, filename=path.name, room=self.current_room, data=encoded)
            print(f"Sending image: {path.name} ({len(data)} bytes)")
        except Exception as exc:
            print(f"Error sending image: {exc}")

    def send_file(self, file_path: str) -> None:
        path = Path(file_path)
        if not path.exists():
            print(f"File not found: {file_path}")
            return
        try:
            data = path.read_bytes()
            transfer_id = str(uuid.uuid4())
            CHUNK_SIZE = 32 * 1024
            chunks = [data[i : i + CHUNK_SIZE] for i in range(0, len(data), CHUNK_SIZE)]
            import base64
            self.send_packet(
                PacketType.FILE_START,
                transfer_id=transfer_id,
                filename=path.name,
                filesize=len(data),
                target_room=self.current_room,
                total_chunks=len(chunks),
            )
            for idx, chunk in enumerate(chunks, start=1):
                encoded = base64.b64encode(chunk).decode("ascii")
                self.send_packet(PacketType.FILE_CHUNK, transfer_id=transfer_id, chunk_index=idx, data=encoded)
            self.send_packet(PacketType.FILE_END, transfer_id=transfer_id)
            print(f"File upload complete: {path.name} ({len(data)} bytes in {len(chunks)} chunks)")
        except Exception as exc:
            print(f"Error sending file: {exc}")

    def print_help(self) -> None:
        print("Available commands:")
        print("  /help                Show this help")
        print("  /online              List online users")
        print("  /join <room>         Join an existing room")
        print("  /create <room>       Create and join a room")
        print("  /leave               Leave the current room")
        print("  /invite <user>       Invite a user to your room")
        print("  /kick <user>         Kick a user from your room")
        print("  /delete <room>       Delete a room you own")
        print("  /matchmake           Enter matchmaking queue")
        print("  /friend <username>   Send a friend request")
        print("  /accept <username>   Accept a friend request")
        print("  /reject <username>   Reject a friend request")
        print("  /remove <username>   Remove a friend")
        print("  /friends             Show your friend list")
        print("  /msg <user> <text>   Send a private message")
        print("  /status <status>     Update your presence status (ONLINE, OFFLINE, IN_ROOM, DO_NOT_DISTURB)")
        print("  /sendimage <path>    Upload an image to current room")
        print("  /sendfile <path>     Upload a file to current room (chunked)")
        print("  /reconnect           Reconnect using session token")
        print("  /quit                Disconnect from the server")
