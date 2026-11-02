import os
import subprocess
import threading
import time
from dataclasses import dataclass

from .errors import CancelledError

POLL_INTERVAL_S = 0.2


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stderr: str


def run_process(
    command: list[str],
    timeout_s: int,
    cancel: threading.Event | None = None,
    env: dict[str, str] | None = None,
) -> ProcessResult:
    if cancel is not None and cancel.is_set():
        raise CancelledError("Cancelled before start")

    deadline = time.monotonic() + timeout_s
    with subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, **env} if env else None,
    ) as process:
        while True:
            try:
                _, stderr = process.communicate(timeout=POLL_INTERVAL_S)
                return ProcessResult(process.returncode, stderr or "")
            except subprocess.TimeoutExpired:
                if cancel is not None and cancel.is_set():
                    _kill(process)
                    raise CancelledError("Cancelled while running") from None
                if time.monotonic() >= deadline:
                    _kill(process)
                    raise subprocess.TimeoutExpired(command, timeout_s) from None


def _kill(process: subprocess.Popen) -> None:
    process.kill()
    process.communicate()
