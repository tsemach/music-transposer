import json
import threading
from typing import TextIO

PROTOCOL_VERSION = "0.1"


def ready() -> dict:
    return {"type": "ready", "version": PROTOCOL_VERSION}


def progress(request_id: int, stage: str, pct: int) -> dict:
    return {"id": request_id, "type": "progress", "stage": stage, "pct": pct}


def result(request_id: int, data: dict) -> dict:
    return {"id": request_id, "type": "result", **data}


def error(request_id: int | None, message: str, code: str = "failed", details: dict | None = None) -> dict:
    reply = {"id": request_id, "type": "error", "message": message, "code": code}
    if details is not None:
        reply["details"] = details
    return reply


class MessageWriter:
    def __init__(self, stream: TextIO):
        self._stream = stream
        self._lock = threading.Lock()

    def send(self, message: dict) -> None:
        line = json.dumps(message, ensure_ascii=False)
        with self._lock:
            self._stream.write(line + "\n")
            self._stream.flush()
