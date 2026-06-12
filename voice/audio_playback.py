"""Audio playback to speaker."""
import threading
from queue import Queue
from typing import Optional

from voice.codec import SAMPLE_RATE, CHANNELS, SAMPLE_WIDTH
from utils.logger import get_logger


class AudioPlayback:
    def __init__(self) -> None:
        self.playback_queue: Queue = Queue()
        self.logger = get_logger("AudioPlayback")
        self.playing = False
        self.play_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start playback from speaker."""
        try:
            import pyaudio

            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                output=True,
            )
            self.playing = True
            self.play_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self.play_thread.start()
            self.logger.info("Audio playback started: %sHz, %d channels", SAMPLE_RATE, CHANNELS)
        except ImportError:
            self.logger.warning("PyAudio not available; audio playback disabled")
            self.playing = False

    def _playback_loop(self) -> None:
        while self.playing:
            try:
                data = self.playback_queue.get(timeout=1)
                if data is None:
                    break
                self.stream.write(data)
            except Exception as exc:
                self.logger.exception("Error playing audio: %s", exc)

    def queue_frame(self, data: bytes) -> None:
        """Add audio frame to playback queue."""
        self.playback_queue.put(data)

    def stop(self) -> None:
        """Stop playback."""
        self.playing = False
        self.playback_queue.put(None)
        try:
            if hasattr(self, "stream"):
                self.stream.stop_stream()
                self.stream.close()
            if hasattr(self, "audio"):
                self.audio.terminate()
            self.logger.info("Audio playback stopped")
        except Exception as exc:
            self.logger.exception("Error stopping playback: %s", exc)
