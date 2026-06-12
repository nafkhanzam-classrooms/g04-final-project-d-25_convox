import threading
from typing import Callable


class Matchmaker:
    def __init__(self):
        self.queue: list[str] = []
        self.lock = threading.RLock()

    def enqueue(self, username: str, on_match: Callable[[list[str]], None]) -> str:
        with self.lock:
            if username in self.queue:
                return "already_queued"
            self.queue.append(username)
            if len(self.queue) >= 2:
                matches = [self.queue.pop(0), self.queue.pop(0)]
                on_match(matches)
                return "matched"
            return "queued"

    def leave_queue(self, username: str) -> None:
        with self.lock:
            if username in self.queue:
                self.queue.remove(username)
