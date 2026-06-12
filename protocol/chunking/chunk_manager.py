import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional

MAX_CHUNK_BUFFER = 20


def generate_transfer_id(sender: str, filename: str, timestamp: str) -> str:
    return f"{sender}:{filename}:{timestamp}"


@dataclass
class ChunkState:
    transfer_id: str
    total_chunks: Optional[int] = None
    received_chunks: Dict[int, bytes] = field(default_factory=dict)
    filename: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)

    def is_complete(self) -> bool:
        if self.total_chunks is None:
            return False
        return len(self.received_chunks) == self.total_chunks

    def missing_chunks(self) -> List[int]:
        if self.total_chunks is None:
            return []
        return [idx for idx in range(1, self.total_chunks + 1) if idx not in self.received_chunks]


class ChunkManager:
    def __init__(self, max_buffer: int = MAX_CHUNK_BUFFER) -> None:
        self.transfers: Dict[str, ChunkState] = {}
        self.lock = threading.RLock()
        self.max_buffer = max_buffer

    def begin_transfer(self, transfer_id: str, filename: str, total_chunks: Optional[int], metadata: Dict[str, str]) -> ChunkState:
        with self.lock:
            if len(self.transfers) >= self.max_buffer:
                oldest = next(iter(self.transfers))
                self.transfers.pop(oldest, None)
            state = ChunkState(transfer_id=transfer_id, total_chunks=total_chunks, filename=filename, metadata=metadata)
            self.transfers[transfer_id] = state
            return state

    def add_chunk(self, transfer_id: str, chunk_index: int, chunk_data: bytes) -> Optional[ChunkState]:
        with self.lock:
            state = self.transfers.get(transfer_id)
            if not state:
                return None
            state.received_chunks[chunk_index] = chunk_data
            return state

    def get_state(self, transfer_id: str) -> Optional[ChunkState]:
        with self.lock:
            return self.transfers.get(transfer_id)

    def complete_transfer(self, transfer_id: str) -> Optional[ChunkState]:
        with self.lock:
            state = self.transfers.get(transfer_id)
            if state and state.is_complete():
                return self.transfers.pop(transfer_id)
            return None

    def cancel_transfer(self, transfer_id: str) -> None:
        with self.lock:
            self.transfers.pop(transfer_id, None)
