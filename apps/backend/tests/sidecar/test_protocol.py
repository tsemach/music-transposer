import io
import json
import threading

from backend.sidecar.protocol import MessageWriter, error, progress, ready, result


def test_message_shapes_match_protocol():
    assert ready() == {"type": "ready", "version": "0.1"}
    assert progress(7, "omr", 40) == {"id": 7, "type": "progress", "stage": "omr", "pct": 40}
    assert result(7, {"pdf": "a.pdf"}) == {"id": 7, "type": "result", "pdf": "a.pdf"}
    assert error(7, "boom") == {"id": 7, "type": "error", "message": "boom", "code": "failed"}


def test_error_includes_details_only_when_given():
    assert "details" not in error(1, "x")
    assert error(1, "x", "validation_failed", {"findings": []})["details"] == {"findings": []}
    assert error(None, "bad json", "invalid_request")["id"] is None


def test_writer_emits_one_utf8_line_per_message():
    stream = io.StringIO()

    MessageWriter(stream).send(result(1, {"pdf": "C:/שירים/שיר.pdf"}))

    line = stream.getvalue()
    assert line.endswith("\n") and line.count("\n") == 1
    assert "שיר.pdf" in line
    assert json.loads(line)["pdf"] == "C:/שירים/שיר.pdf"


def test_concurrent_senders_never_interleave_lines():
    stream = io.StringIO()
    writer = MessageWriter(stream)

    def spam(worker: int) -> None:
        for index in range(50):
            writer.send(progress(worker, "omr", index))

    threads = [threading.Thread(target=spam, args=(worker,)) for worker in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    lines = stream.getvalue().splitlines()
    assert len(lines) == 400
    assert all(json.loads(line)["type"] == "progress" for line in lines)
