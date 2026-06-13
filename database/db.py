import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(__file__), "convox.db")


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.ensure_schema()

    def execute(self, query: str, params: Tuple[Any, ...] = ()) -> sqlite3.Cursor:
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        self.connection.commit()
        return cursor

    def ensure_schema(self) -> None:
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL DEFAULT 'OFFLINE',
                created_at TEXT NOT NULL
            )
            """
        )
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS friend_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(sender_id, receiver_id)
            )
            """
        )
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS friends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                friend_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, friend_id)
            )
            """
        )
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                owner_id INTEGER NOT NULL,
                visibility TEXT NOT NULL,
                max_capacity INTEGER NOT NULL,
                invite_only INTEGER NOT NULL,
                password TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS room_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                joined_at TEXT NOT NULL,
                UNIQUE(room_id, user_id)
            )
            """
        )
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS room_invites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL,
                inviter_id INTEGER NOT NULL,
                invitee_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(room_id, invitee_id)
            )
            """
        )
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER,
                room_id INTEGER,
                message_type TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_room TEXT NOT NULL,
                message TEXT NOT NULL,
                send_time TEXT NOT NULL,
                sent INTEGER NOT NULL DEFAULT 0,
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS file_transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transfer_id TEXT UNIQUE NOT NULL,
                sender_id INTEGER NOT NULL,
                target_room TEXT,
                target_user TEXT,
                filename TEXT NOT NULL,
                filesize INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                transfer_type TEXT NOT NULL,
                status TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_token TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                room_name TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            )
            """
        )

    def get_or_create_user(self, username: str) -> int:
        if not username:
            raise ValueError("Username cannot be empty")
        row = self.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if row:
            return row["id"]
        cursor = self.execute(
            "INSERT INTO users (username, created_at, status) VALUES (?, ?, ?)",
            (username, datetime.utcnow().isoformat(), "ONLINE"),
        )
        return cursor.lastrowid

    def find_user_id(self, username: str) -> Optional[int]:
        row = self.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        return row["id"] if row else None

    def find_username(self, user_id: int) -> Optional[str]:
        row = self.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
        return row["username"] if row else None

    def update_user_status(self, username: str, status: str) -> None:
        self.execute("UPDATE users SET status = ? WHERE username = ?", (status, username))

    def friend_request_exists(self, sender: str, receiver: str) -> bool:
        sender_id = self.find_user_id(sender)
        receiver_id = self.find_user_id(receiver)
        if sender_id is None or receiver_id is None:
            return False
        row = self.execute(
            "SELECT id FROM friend_requests WHERE sender_id = ? AND receiver_id = ? AND status = 'PENDING'",
            (sender_id, receiver_id),
        ).fetchone()
        return row is not None

    def create_friend_request(self, sender: str, receiver: str) -> None:
        sender_id = self.get_or_create_user(sender)
        receiver_id = self.find_user_id(receiver)
        if receiver_id is None:
            raise ValueError(f"User '{receiver}' does not exist.")

        existing = self.execute(
            "SELECT status FROM friend_requests WHERE sender_id = ? AND receiver_id = ?",
            (sender_id, receiver_id),
        ).fetchone()
        if existing:
            if existing["status"] == "PENDING":
                return
            self.execute(
                "UPDATE friend_requests SET status = ?, created_at = ? WHERE sender_id = ? AND receiver_id = ?",
                ("PENDING", datetime.utcnow().isoformat(), sender_id, receiver_id),
            )
            return

        self.execute(
            "INSERT INTO friend_requests (sender_id, receiver_id, status, created_at) VALUES (?, ?, ?, ?)",
            (sender_id, receiver_id, "PENDING", datetime.utcnow().isoformat()),
        )

    def respond_friend_request(self, sender: str, receiver: str, accept: bool) -> None:
        sender_id = self.find_user_id(sender)
        receiver_id = self.find_user_id(receiver)
        if sender_id is None or receiver_id is None:
            raise ValueError("Invalid user in friend request response.")
        status = "ACCEPTED" if accept else "REJECTED"
        self.execute(
            "UPDATE friend_requests SET status = ? WHERE sender_id = ? AND receiver_id = ? AND status = 'PENDING'",
            (status, sender_id, receiver_id),
        )
        if accept:
            self.add_friend_by_id(sender_id, receiver_id)
            self.add_friend_by_id(receiver_id, sender_id)

    def list_pending_friend_requests(self, username: str) -> List[str]:
        user_id = self.find_user_id(username)
        if user_id is None:
            return []
        cursor = self.execute(
            "SELECT u.username FROM friend_requests fr JOIN users u ON fr.sender_id = u.id WHERE fr.receiver_id = ? AND fr.status = 'PENDING' ORDER BY fr.created_at ASC",
            (user_id,),
        )
        return [row["username"] for row in cursor.fetchall()]

    def add_friend_by_id(self, user_id: int, friend_id: int) -> None:
        self.execute(
            "INSERT OR IGNORE INTO friends (user_id, friend_id, created_at) VALUES (?, ?, ?)",
            (user_id, friend_id, datetime.utcnow().isoformat()),
        )

    def list_friends(self, username: str) -> List[Dict[str, str]]:
        if self.find_user_id(username) is None:
            return []
        cursor = self.execute(
            """
            SELECT u2.username as friend_name, u2.status as status
            FROM friends f
            JOIN users u1 ON f.user_id = u1.id
            JOIN users u2 ON f.friend_id = u2.id
            WHERE u1.username = ?
            ORDER BY u2.username
            """,
            (username,),
        )
        return [dict(record) for record in cursor.fetchall()]

    def are_friends(self, username: str, friend_name: str) -> bool:
        sender_id = self.find_user_id(username)
        receiver_id = self.find_user_id(friend_name)
        if sender_id is None or receiver_id is None:
            return False
        row = self.execute(
            "SELECT id FROM friends WHERE user_id = ? AND friend_id = ?",
            (sender_id, receiver_id),
        ).fetchone()
        return row is not None

    def remove_friend(self, username: str, friend_name: str) -> None:
        sender_id = self.find_user_id(username)
        receiver_id = self.find_user_id(friend_name)
        if sender_id is None or receiver_id is None:
            return
        self.execute(
            "DELETE FROM friends WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)",
            (sender_id, receiver_id, receiver_id, sender_id),
        )

    def create_room(
        self,
        name: str,
        owner: str,
        visibility: str = "public",
        max_capacity: int = 50,
        invite_only: bool = False,
        password: Optional[str] = None,
    ) -> bool:
        owner_id = self.get_or_create_user(owner)
        if self.get_room(name) is not None:
            return False
        self.execute(
            "INSERT INTO rooms (name, owner_id, visibility, max_capacity, invite_only, password, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, owner_id, visibility, max_capacity, int(invite_only), password, datetime.utcnow().isoformat()),
        )
        return True

    def get_room(self, name: str) -> Optional[Dict[str, Any]]:
        row = self.execute("SELECT * FROM rooms WHERE name = ?", (name,)).fetchone()
        return dict(row) if row else None

    def delete_room(self, name: str) -> None:
        room = self.get_room(name)
        if room is None:
            return
        room_id = room["id"]
        self.execute("DELETE FROM room_invites WHERE room_id = ?", (room_id,))
        self.execute("DELETE FROM room_members WHERE room_id = ?", (room_id,))
        self.execute("DELETE FROM rooms WHERE id = ?", (room_id,))

    def add_room_member(self, room_name: str, username: str) -> None:
        room = self.get_room(room_name)
        user_id = self.get_or_create_user(username)
        if room is None:
            raise ValueError("Room does not exist.")
        self.execute(
            "INSERT OR IGNORE INTO room_members (room_id, user_id, joined_at) VALUES (?, ?, ?)",
            (room["id"], user_id, datetime.utcnow().isoformat()),
        )

    def remove_room_member(self, room_name: str, username: str) -> None:
        room = self.get_room(room_name)
        user_id = self.find_user_id(username)
        if room is None or user_id is None:
            return
        self.execute(
            "DELETE FROM room_members WHERE room_id = ? AND user_id = ?",
            (room["id"], user_id),
        )

    def list_room_members(self, room_name: str) -> List[str]:
        room = self.get_room(room_name)
        if room is None:
            return []
        cursor = self.execute(
            """
            SELECT u.username FROM room_members rm
            JOIN users u ON rm.user_id = u.id
            WHERE rm.room_id = ?
            ORDER BY u.username
            """,
            (room["id"],),
        )
        return [row["username"] for row in cursor.fetchall()]

    def invite_room_user(self, room_name: str, inviter: str, invitee: str) -> None:
        room = self.get_room(room_name)
        inviter_id = self.find_user_id(inviter)
        invitee_id = self.find_user_id(invitee)
        if room is None or inviter_id is None or invitee_id is None:
            raise ValueError("Invalid invitation data.")
        self.execute(
            "INSERT OR IGNORE INTO room_invites (room_id, inviter_id, invitee_id, created_at) VALUES (?, ?, ?, ?)",
            (room["id"], inviter_id, invitee_id, datetime.utcnow().isoformat()),
        )

    def is_room_invited(self, room_name: str, username: str) -> bool:
        room = self.get_room(room_name)
        user_id = self.find_user_id(username)
        if room is None or user_id is None:
            return False
        row = self.execute(
            "SELECT id FROM room_invites WHERE room_id = ? AND invitee_id = ?",
            (room["id"], user_id),
        ).fetchone()
        return row is not None

    def save_message(
        self,
        sender: str,
        content: str,
        message_type: str,
        room_name: Optional[str] = None,
        target: Optional[str] = None,
    ) -> None:
        sender_id = self.get_or_create_user(sender)
        receiver_id = self.find_user_id(target) if target else None
        room_id = self.get_room(room_name)["id"] if room_name else None
        self.execute(
            "INSERT INTO messages (sender_id, receiver_id, room_id, message_type, content, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (sender_id, receiver_id, room_id, message_type, content, datetime.utcnow().isoformat()),
        )

    def save_file_transfer(
        self,
        transfer_id: str,
        sender: str,
        target_room: Optional[str],
        target_user: Optional[str],
        filename: str,
        filesize: int,
        file_path: str,
        transfer_type: str,
        status: str,
    ) -> None:
        sender_id = self.get_or_create_user(sender)
        self.execute(
            "INSERT OR REPLACE INTO file_transfers (transfer_id, sender_id, target_room, target_user, filename, filesize, file_path, transfer_type, status, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (transfer_id, sender_id, target_room, target_user, filename, filesize, file_path, transfer_type, status, datetime.utcnow().isoformat()),
        )

    def update_file_transfer_status(self, transfer_id: str, status: str) -> None:
        self.execute(
            "UPDATE file_transfers SET status = ? WHERE transfer_id = ?",
            (status, transfer_id),
        )

    def create_session(self, session_token: str, username: str, room_name: str) -> None:
        self.execute(
            "INSERT OR REPLACE INTO sessions (session_token, username, room_name, last_seen, active) VALUES (?, ?, ?, ?, 1)",
            (session_token, username, room_name, datetime.utcnow().isoformat()),
        )

    def refresh_session(self, session_token: str) -> None:
        self.execute(
            "UPDATE sessions SET last_seen = ?, active = 1 WHERE session_token = ?",
            (datetime.utcnow().isoformat(), session_token),
        )

    def get_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        row = self.execute("SELECT * FROM sessions WHERE session_token = ? AND active = 1", (session_token,)).fetchone()
        return dict(row) if row else None

    def expire_sessions_older_than(self, minutes: int = 15) -> None:
        threshold = datetime.utcnow() - timedelta(minutes=minutes)
        self.execute(
            "UPDATE sessions SET active = 0 WHERE last_seen < ?",
            (threshold.isoformat(),),
        )

    def fetch_room_messages(self, room_name: str, limit: int = 50) -> List[Dict[str, str]]:
        room = self.get_room(room_name)
        if room is None:
            return []
        cursor = self.execute(
            """
            SELECT u.username as sender, m.content, m.timestamp
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.room_id = ?
            ORDER BY m.id DESC
            LIMIT ?
            """,
            (room["id"], limit),
        )
        rows = [dict(row) for row in cursor.fetchall()]
        return list(reversed(rows))

    def fetch_private_messages(self, user_one: str, user_two: str, limit: int = 50) -> List[Dict[str, str]]:
        first_id = self.find_user_id(user_one)
        second_id = self.find_user_id(user_two)
        if first_id is None or second_id is None:
            return []
        cursor = self.execute(
            """
            SELECT u.username as sender, m.content, m.timestamp, r.username as target
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            JOIN users r ON m.receiver_id = r.id
            WHERE (m.sender_id = ? AND m.receiver_id = ?) OR (m.sender_id = ? AND m.receiver_id = ?)
            ORDER BY m.id DESC
            LIMIT ?
            """,
            (first_id, second_id, second_id, first_id, limit),
        )
        rows = [dict(row) for row in cursor.fetchall()]
        return list(reversed(rows))

    def create_scheduled_broadcast(self, target_room: str, message: str, send_time: str, created_by: str) -> None:
        creator_id = self.get_or_create_user(created_by)
        self.execute(
            "INSERT INTO broadcasts (target_room, message, send_time, sent, created_by, created_at) VALUES (?, ?, ?, 0, ?, ?)",
            (target_room, message, send_time, creator_id, datetime.utcnow().isoformat()),
        )

    def fetch_due_broadcasts(self) -> List[Dict[str, Any]]:
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self.execute(
            "SELECT * FROM broadcasts WHERE sent = 0 AND send_time <= ? ORDER BY send_time ASC",
            (now,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def mark_broadcast_sent(self, broadcast_id: int) -> None:
        self.execute("UPDATE broadcasts SET sent = 1 WHERE id = ?", (broadcast_id,))
