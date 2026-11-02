import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass

from .errors import CancelledError

POLL_INTERVAL_S = 0.2
KILL_WAIT_S = 5
IS_WINDOWS = os.name == "nt"


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
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, **env} if env else None,
        start_new_session=not IS_WINDOWS,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if IS_WINDOWS else 0,
    ) as process:
        while True:
            try:
                _, stderr = process.communicate(timeout=POLL_INTERVAL_S)
                return ProcessResult(process.returncode, stderr or "")
            except subprocess.TimeoutExpired:
                if cancel is not None and cancel.is_set():
                    _kill_tree(process)
                    raise CancelledError("Cancelled while running") from None
                if time.monotonic() >= deadline:
                    _kill_tree(process)
                    raise subprocess.TimeoutExpired(command, timeout_s) from None


def _kill_tree(process: subprocess.Popen) -> None:
    if IS_WINDOWS:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True, check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.communicate(timeout=KILL_WAIT_S)
    except subprocess.TimeoutExpired:
        process.kill()
