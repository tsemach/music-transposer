import io
import json
import queue
import threading
import time

import pytest

from backend.errors import CancelledError
from backend.sidecar.protocol import MessageWriter
from backend.sidecar.server import serve


def echo(params, ctx):
    return {"echo": params}


def progressive(params, ctx):
    ctx.progress("stage-a", 10)
    return {"ok": True}


def boom(params, ctx):
    raise RuntimeError("kaboom")


def slow(params, ctx):
    if ctx.cancel.wait(20):
        raise CancelledError("stopped")
    return {"finished": True}


HANDLERS = {"echo": echo, "progressive": progressive, "boom": boom, "slow": slow}


class Harness:
    def __init__(self):
        self._lines: queue.Queue = queue.Queue()
        self._output = io.StringIO()
        self._thread = threading.Thread(
            target=serve, args=(iter(self._lines.get, None), MessageWriter(self._output), HANDLERS), daemon=True
        )
        self._thread.start()

    def send(self, message) -> None:
        self._lines.put(message if isinstance(message, str) else json.dumps(message, ensure_ascii=False))

    def messages(self) -> list[dict]:
        return [json.loads(line) for line in self._output.getvalue().splitlines()]

    def wait_for(self, predicate, timeout: float = 5.0) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for message in self.messages():
                if predicate(message):
                    return message
            time.sleep(0.01)
        raise AssertionError(f"no matching message; got {self.messages()}")

    def close(self, timeout: float = 5.0) -> None:
        self._lines.put(None)
        self._thread.join(timeout)
        assert not self._thread.is_alive(), "serve did not exit after EOF"


@pytest.fixture
def harness():
    instance = Harness()
    yield instance
    instance.close()


def reply_for(request_id):
    return lambda message: message.get("id") == request_id and message["type"] in ("result", "error")


def test_ready_is_first_message(harness):
    assert harness.wait_for(lambda m: True) == {"type": "ready", "version": "0.1"}


def test_result_echoes_id(harness):
    harness.send({"id": 3, "cmd": "echo", "params": {"x": 1}})

    assert harness.wait_for(reply_for(3)) == {"id": 3, "type": "result", "echo": {"x": 1}}


def test_progress_then_result(harness):
    harness.send({"id": 4, "cmd": "progressive"})
    harness.wait_for(reply_for(4))

    types = [m["type"] for m in harness.messages() if m.get("id") == 4]
    assert types == ["progress", "result"]


def test_malformed_json_replies_error_and_continues(harness):
    harness.send("this is not json")
    harness.send({"id": 1, "cmd": "echo"})

    error = harness.wait_for(lambda m: m["type"] == "error")
    assert (error["id"], error["code"]) == (None, "invalid_request")
    assert harness.wait_for(reply_for(1))["type"] == "result"


def test_missing_id_or_cmd_replies_error(harness):
    harness.send({"cmd": "echo"})
    harness.send({"id": 5})

    errors = []
    harness.wait_for(lambda m: m["type"] == "error" and m["id"] is None)
    errors.append(harness.wait_for(reply_for(5)))
    assert errors[0]["code"] == "invalid_request"


def test_unknown_command_replies_error_with_id(harness):
    harness.send({"id": 9, "cmd": "nope"})

    reply = harness.wait_for(reply_for(9))
    assert (reply["type"], reply["code"]) == ("error", "unknown_command")


def test_handler_exception_becomes_error_reply(harness):
    harness.send({"id": 2, "cmd": "boom"})

    reply = harness.wait_for(reply_for(2))
    assert (reply["code"], "kaboom" in reply["message"]) == ("internal", True)


def test_concurrent_requests_get_independent_replies(harness):
    harness.send({"id": 1, "cmd": "slow"})
    harness.send({"id": 2, "cmd": "echo", "params": {"fast": True}})

    assert harness.wait_for(reply_for(2))["echo"] == {"fast": True}
    assert not any(reply_for(1)(m) for m in harness.messages())


def test_cancel_stops_target_only(harness):
    harness.send({"id": 1, "cmd": "slow"})
    harness.send({"id": 2, "cmd": "slow"})
    harness.send({"id": 3, "cmd": "cancel", "params": {"target": 1}})

    assert harness.wait_for(reply_for(3))["cancelled"] is True
    assert harness.wait_for(reply_for(1))["code"] == "cancelled"
    assert not any(reply_for(2)(m) for m in harness.messages())


def test_cancel_unknown_id_replies_false(harness):
    harness.send({"id": 1, "cmd": "cancel", "params": {"target": 99}})

    assert harness.wait_for(reply_for(1))["cancelled"] is False


def test_eof_cancels_running_work_and_exits_promptly():
    harness = Harness()
    harness.send({"id": 1, "cmd": "slow"})
    harness.wait_for(lambda m: m["type"] == "ready")
    started = time.monotonic()

    harness.close(timeout=5)

    assert time.monotonic() - started < 5
    assert harness.wait_for(reply_for(1))["code"] == "cancelled"


def test_hebrew_params_round_trip(harness):
    path = "C:/שירים/שיר ראשון.pdf"
    harness.send({"id": 1, "cmd": "echo", "params": {"path": path}})

    assert harness.wait_for(reply_for(1))["echo"]["path"] == path


def test_malformed_cancel_target_replies_error_and_loop_survives(harness):
    harness.send({"id": 1, "cmd": "cancel", "params": {"target": [1]}})
    harness.send({"id": 2, "cmd": "echo", "params": {"ok": True}})

    assert harness.wait_for(reply_for(1))["code"] == "invalid_request"
    assert harness.wait_for(reply_for(2))["echo"] == {"ok": True}
