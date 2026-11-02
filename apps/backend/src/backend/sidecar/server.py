import json
import threading
import time
from collections.abc import Callable, Iterable

from .handlers import HANDLERS, Handler, RequestContext, classify
from .protocol import MessageWriter, error, progress, ready, result

SHUTDOWN_GRACE_S = 10


class _BadRequest(Exception):
    def __init__(self, request_id: int | None, message: str):
        super().__init__(message)
        self.request_id = request_id


class _Requests:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running: dict[int, tuple[threading.Thread, threading.Event]] = {}

    def start(self, request_id: int, run: Callable[[threading.Event], None]) -> threading.Event | None:
        cancel = threading.Event()
        with self._lock:
            if request_id in self._running:
                return None
            thread = threading.Thread(target=run, args=(cancel,), daemon=True)
            self._running[request_id] = (thread, cancel)
        thread.start()
        return cancel

    def finish(self, request_id: int) -> None:
        with self._lock:
            self._running.pop(request_id, None)

    def cancel(self, request_id: int) -> bool:
        with self._lock:
            entry = self._running.get(request_id)
        if entry is None:
            return False
        entry[1].set()
        return True

    def cancel_all_and_wait(self, grace_s: float) -> None:
        with self._lock:
            entries = list(self._running.values())
        for _, cancel in entries:
            cancel.set()
        deadline = time.monotonic() + grace_s
        for thread, _ in entries:
            thread.join(max(0.0, deadline - time.monotonic()))


def serve(stdin: Iterable[str], writer: MessageWriter, handlers: dict[str, Handler] = HANDLERS) -> None:
    writer.send(ready())
    requests = _Requests()
    for line in stdin:
        if not line.strip():
            continue
        try:
            _dispatch(line, writer, handlers, requests)
        except Exception as failure:
            writer.send(error(None, f"Could not process request: {failure}", "internal"))
    requests.cancel_all_and_wait(SHUTDOWN_GRACE_S)


def _dispatch(line: str, writer: MessageWriter, handlers: dict[str, Handler], requests: _Requests) -> None:
    try:
        request_id, command, params = _parse(line)
    except _BadRequest as bad:
        writer.send(error(bad.request_id, str(bad), "invalid_request"))
        return
    if command == "cancel":
        target = params.get("target")
        if not isinstance(target, int) or isinstance(target, bool):
            writer.send(error(request_id, "cancel needs an integer target", "invalid_request"))
            return
        writer.send(result(request_id, {"cancelled": requests.cancel(target)}))
    elif command not in handlers:
        writer.send(error(request_id, f"Unknown command: {command}", "unknown_command"))
    else:
        _launch(request_id, handlers[command], params, writer, requests)


def _launch(request_id: int, handler: Handler, params: dict, writer: MessageWriter, requests: _Requests) -> None:
    def run(cancel: threading.Event) -> None:
        context = RequestContext(lambda stage, pct: writer.send(progress(request_id, stage, pct)), cancel)
        try:
            writer.send(result(request_id, handler(params, context)))
        except Exception as failure:
            code, message, details = classify(failure)
            writer.send(error(request_id, message, code, details))
        finally:
            requests.finish(request_id)

    if requests.start(request_id, run) is None:
        writer.send(error(request_id, "Request id already in use", "invalid_request"))


def _parse(line: str) -> tuple[int, str, dict]:
    try:
        message = json.loads(line)
    except json.JSONDecodeError:
        raise _BadRequest(None, "Request is not valid JSON") from None
    if not isinstance(message, dict):
        raise _BadRequest(None, "Request must be a JSON object")
    request_id = message.get("id")
    if not isinstance(request_id, int) or isinstance(request_id, bool):
        raise _BadRequest(None, "Request needs an integer id")
    command = message.get("cmd")
    params = message.get("params", {})
    if not isinstance(command, str) or not isinstance(params, dict):
        raise _BadRequest(request_id, "Request needs a string cmd and object params")
    return request_id, command, params
