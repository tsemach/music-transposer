import json
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from backend.audiveris_locator import find_audiveris
from backend.errors import ExecutableNotFoundError
from backend.musescore_locator import find_musescore

SHEETS = Path(__file__).resolve().parents[4] / "sheets"


def tools_available() -> bool:
    try:
        find_audiveris()
        find_musescore()
    except ExecutableNotFoundError:
        return False
    return SHEETS.is_dir()


pytestmark = pytest.mark.skipif(not tools_available(), reason="needs Audiveris, MuseScore and sample sheets")


class Sidecar:
    def __init__(self) -> None:
        self.process = subprocess.Popen(
            [sys.executable, "-m", "backend", "serve"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
        )
        self.messages: queue.Queue = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self) -> None:
        for line in self.process.stdout:
            self.messages.put(json.loads(line))

    def send(self, message: dict) -> None:
        self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def next(self, timeout: float = 20.0) -> dict:
        return self.messages.get(timeout=timeout)

    def until(self, predicate, timeout: float = 120.0) -> list[dict]:
        seen = []
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            message = self.next(deadline - time.monotonic())
            seen.append(message)
            if predicate(message):
                return seen
        raise AssertionError(f"timed out; saw {seen}")


@pytest.fixture
def sidecar():
    instance = Sidecar()
    yield instance
    if instance.process.poll() is None:
        instance.process.kill()


def test_ready_then_doctor(sidecar):
    assert sidecar.next() == {"type": "ready", "version": "0.1"}

    sidecar.send({"id": 1, "cmd": "doctor"})

    reply = sidecar.next()
    assert reply["id"] == 1 and reply["audiveris"] and reply["musescore"]


def test_unknown_command_error_keeps_process_alive(sidecar):
    sidecar.next()
    sidecar.send({"id": 1, "cmd": "nope"})
    assert sidecar.next()["code"] == "unknown_command"

    sidecar.send({"id": 2, "cmd": "doctor"})

    assert sidecar.next()["id"] == 2


def test_pipeline_on_hebrew_named_copy_of_funk_out(sidecar, tmp_path):
    pdf = tmp_path / "פאנק אאוט.pdf"
    shutil.copy(SHEETS / "funk-out-alto-saxophone.pdf", pdf)
    sidecar.next()

    sidecar.send({"id": 7, "cmd": "pipeline", "params": {"pdf": str(pdf), "source": "alto"}})
    seen = sidecar.until(lambda m: m["type"] in ("result", "error"))

    stages = [m["stage"] for m in seen if m["type"] == "progress"]
    final = seen[-1]
    assert stages == ["omr", "validate", "transpose", "render", "done"]
    assert final["type"] == "result" and final["id"] == 7
    assert Path(final["pdf"]).is_file() and Path(final["pdf"]).suffix == ".pdf"


def test_cancel_kills_running_pipeline_quickly(sidecar, tmp_path):
    pdf = tmp_path / "gymnopedie.pdf"
    shutil.copy(SHEETS / "gymnopedie-no-1-alto-saxophone.pdf", pdf)
    sidecar.next()
    sidecar.send({"id": 1, "cmd": "pipeline", "params": {"pdf": str(pdf), "source": "alto"}})
    sidecar.until(lambda m: m["type"] == "progress" and m["stage"] == "omr")
    time.sleep(1)
    started = time.monotonic()

    sidecar.send({"id": 2, "cmd": "cancel", "params": {"target": 1}})
    seen = sidecar.until(lambda m: m["id"] == 1 and m["type"] in ("result", "error"), timeout=15)

    assert seen[-1]["code"] == "cancelled"
    assert time.monotonic() - started < 10


def test_closing_stdin_exits_process(sidecar):
    sidecar.next()

    sidecar.process.stdin.close()

    assert sidecar.process.wait(timeout=10) == 0
