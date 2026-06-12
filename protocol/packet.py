import json
from enum import Enum
from typing import Any, Dict, Optional

MAX_PACKET_SIZE = 10 * 1024 * 1024


class PacketType(str, Enum):
    LOGIN = "LOGIN"
    MESSAGE = "MESSAGE"
    PRIVATE_MESSAGE = "PRIVATE_MESSAGE"
    JOIN_ROOM = "JOIN_ROOM"
    LEAVE_ROOM = "LEAVE_ROOM"
    CREATE_ROOM = "CREATE_ROOM"
    DELETE_ROOM = "DELETE_ROOM"
    INVITE_USER = "INVITE_USER"
    KICK_USER = "KICK_USER"
    ADD_FRIEND = "ADD_FRIEND"
    ACCEPT_FRIEND = "ACCEPT_FRIEND"
    REJECT_FRIEND = "REJECT_FRIEND"
    REMOVE_FRIEND = "REMOVE_FRIEND"
    GET_FRIENDS = "GET_FRIENDS"
    FRIEND_REQUEST = "FRIEND_REQUEST"
    FRIEND_LIST = "FRIEND_LIST"
    GET_ONLINE_USERS = "GET_ONLINE_USERS"
    STATUS_UPDATE = "STATUS_UPDATE"
    UPDATE_STATUS = "UPDATE_STATUS"
    MATCHMAKE = "MATCHMAKE"
    BROADCAST = "BROADCAST"
    SCHEDULE_BROADCAST = "SCHEDULE_BROADCAST"
    IMAGE = "IMAGE"
    FILE = "FILE"
    FILE_START = "FILE_START"
    FILE_CHUNK = "FILE_CHUNK"
    FILE_END = "FILE_END"
    RECONNECT = "RECONNECT"
    SESSION_ACK = "SESSION_ACK"
    TRANSFER_PROGRESS = "TRANSFER_PROGRESS"
    ROOM_HISTORY = "ROOM_HISTORY"
    VOICE_START = "VOICE_START"
    VOICE_STOP = "VOICE_STOP"
    VOICE_STATUS = "VOICE_STATUS"
    SYSTEM = "SYSTEM"
    ERROR = "ERROR"


def build_packet(packet_type: PacketType, **fields: Any) -> bytes:
    packet: Dict[str, Any] = {"type": packet_type.value}
    packet.update(fields)
    payload = json.dumps(packet, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return len(payload).to_bytes(4, "big") + payload


def recvall(sock, length: int) -> Optional[bytes]:
    data = bytearray()
    while len(data) < length:
        packet = sock.recv(length - len(data))
        if not packet:
            return None
        data.extend(packet)
    return bytes(data)


def receive_packet(sock) -> Optional[Dict[str, Any]]:
    header = recvall(sock, 4)
    if not header:
        return None
    length = int.from_bytes(header, "big")
    if length <= 0 or length > MAX_PACKET_SIZE:
        return None
    payload = recvall(sock, length)
    if not payload:
        return None
    try:
        return json.loads(payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
