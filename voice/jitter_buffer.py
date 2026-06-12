"""Jitter buffer for voice streaming."""
import threading
from collections import OrderedDict
from typing import Optional

BUFFER_SIZE = 50
MAX_LATENCY_MS = 200


class JitterBuffer:
    def __init__(self, max_frames: int = BUFFER_SIZE, max_latency_ms: int = MAX_LATENCY_MS) -> None:
        self.buffer: OrderedDict[int, bytes] = OrderedDict()
        self.next_sequence = 0
        self.max_frames = max_frames
        self.max_latency_ms = max_latency_ms
        self.lock = threading.RLock()
        self.started = False

    def add_frame(self, sequence: int, data: bytes) -> None:
        """Add audio frame to buffer."""
        with self.lock:
            if not self.started:
                self.next_sequence = sequence
                self.started = True
            if sequence in self.buffer:
                return
            self.buffer[sequence] = data
            if len(self.buffer) > self.max_frames:
                oldest_seq = next(iter(self.buffer))
                self.buffer.pop(oldest_seq, None)

    def get_frame(self) -> Optional[bytes]:
        """Get next playback frame from buffer."""
        with self.lock:
            if self.next_sequence not in self.buffer:
                return None
            data = self.buffer.pop(self.next_sequence)
            self.next_sequence += 1
            return data

    def missing_frames(self) -> list[int]:
        """Return list of missing sequence numbers."""
        with self.lock:
            if not self.buffer:
                return []
            first_seq = min(self.buffer.keys())
            last_seq = max(self.buffer.keys())
            return [i for i in range(first_seq, last_seq) if i not in self.buffer and i < self.next_sequence]

    def flush(self) -> None:
        """Clear buffer."""
        with self.lock:
            self.buffer.clear()
            self.started = False

    def buffer_size(self) -> int:
        """Current buffer occupancy."""
        with self.lock:
            return len(self.buffer)
