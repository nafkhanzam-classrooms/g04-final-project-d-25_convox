import threading
from typing import Callable, Optional


class TimerManager:
    def __init__(self):
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

    def start(self, target: Callable[[], None]) -> None:
        self.thread = threading.Thread(target=target, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)
