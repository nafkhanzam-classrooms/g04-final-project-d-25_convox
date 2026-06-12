from typing import Any


class FileTransfer:
    def prepare_transfer(self, filename: str, sender: str) -> dict[str, Any]:
        return {
            "status": "ready",
            "sender": sender,
            "filename": filename,
        }

    def save_transfer(self, data: bytes, filename: str) -> str:
        path = f"received_{filename}"
        with open(path, "wb") as stream:
            stream.write(data)
        return path
