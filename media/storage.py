from pathlib import Path

from storage.storage_manager import StorageManager

storage_manager = StorageManager()


def room_media_path(room: str, filename: str) -> Path:
    return storage_manager.room_upload_path(room, filename)


def user_download_path(filename: str) -> Path:
    return storage_manager.download_path(filename)


def temp_transfer_path(transfer_id: str) -> Path:
    return storage_manager.temp_path(transfer_id)
