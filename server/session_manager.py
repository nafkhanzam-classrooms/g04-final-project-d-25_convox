import threading
import uuid
from typing import Dict, Optional

from database.db import Database
from utils.helper import timestamp
from utils.logger import get_logger


class SessionManager:
    def __init__(self, database: Database):
        self.database = database
        self.sessions: Dict[str, str] = {}
        self.lock = threading.RLock()
        self.logger = get_logger("SessionManager")

    def create_session(self, username: str, room_name: str) -> str:
        session_token = str(uuid.uuid4())
        self.database.create_session(session_token, username, room_name)
        with self.lock:
            self.sessions[username] = session_token
        self.logger.info("Created session %s for %s in room %s", session_token, username, room_name)
        return session_token

    def restore_session(self, session_token: str) -> Optional[Dict[str, str]]:
        self.database.expire_sessions_older_than(15)
        session = self.database.get_session(session_token)
        if not session:
            self.logger.warning("Failed to restore session token %s", session_token)
            return None
        self.database.refresh_session(session_token)
        self.logger.info("Restored session token %s for %s", session_token, session["username"])
        return {
            "username": session["username"],
            "room_name": session["room_name"],
            "session_token": session_token,
        }

    def refresh_session(self, session_token: str) -> None:
        self.database.refresh_session(session_token)

    def end_session(self, username: str) -> None:
        with self.lock:
            session_token = self.sessions.pop(username, None)
            if session_token:
                self.database.execute("UPDATE sessions SET active = 0 WHERE session_token = ?", (session_token,))
                self.logger.info("Ended session %s for %s", session_token, username)
