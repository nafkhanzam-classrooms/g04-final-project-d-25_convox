import threading
from datetime import datetime
from typing import Callable

from database.db import Database
from utils.logger import get_logger


class ScheduledBroadcastRunner:
    def __init__(self, database: Database, broadcast_callback: Callable[[str, str], None]) -> None:
        self.database = database
        self.broadcast_callback = broadcast_callback
        self.stop_event = threading.Event()
        self.logger = get_logger("ScheduledBroadcastRunner")
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def schedule(self, target_room: str, message: str, send_time: str, requested_by: str) -> None:
        self.database.create_scheduled_broadcast(target_room, message, send_time, requested_by)
        self.logger.info("Scheduled broadcast to %s at %s", target_room, send_time)

    def _run(self) -> None:
        while not self.stop_event.is_set():
            broadcasts = self.database.fetch_due_broadcasts()
            for broadcast in broadcasts:
                room_name = broadcast["target_room"]
                message = broadcast["message"]
                self.logger.info("Dispatching scheduled broadcast to %s", room_name)
                self.broadcast_callback(room_name, message)
                self.database.mark_broadcast_sent(broadcast["id"])
            self.stop_event.wait(5)

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=2)
