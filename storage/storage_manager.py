import os
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
DOWNLOADS_DIR = BASE_DIR / "downloads"
TEMP_DIR = BASE_DIR / "temp"

for directory in (UPLOADS_DIR, DOWNLOADS_DIR, TEMP_DIR):
    directory.mkdir(exist_ok=True)


class StorageManager:
    def __init__(self) -> None:
        self.uploads = UPLOADS_DIR
        self.downloads = DOWNLOADS_DIR
        self.temp = TEMP_DIR

    def room_upload_path(self, room: str, filename: str) -> Path:
        target = self.uploads / room
        target.mkdir(parents=True, exist_ok=True)
        return target / filename

    def user_upload_path(self, username: str, filename: str) -> Path:
        target = self.uploads / username
        target.mkdir(parents=True, exist_ok=True)
        return target / filename

    def download_path(self, filename: str) -> Path:
        target = self.downloads
        return target / filename

    def temp_path(self, transfer_id: str) -> Path:
        target = self.temp / transfer_id
        target.mkdir(parents=True, exist_ok=True)
        return target

    def save_file(self, path: Path, data: bytes) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def cleanup_temp(self, transfer_id: str) -> None:
        path = self.temp / transfer_id
        if path.exists() and path.is_dir():
            for child in path.iterdir():
                if child.is_file():
                    child.unlink()
            path.rmdir()
