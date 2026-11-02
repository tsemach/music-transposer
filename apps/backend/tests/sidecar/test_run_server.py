import io
import json

from backend.sidecar.main import run_server


def test_stray_print_does_not_reach_protocol_stream(capsys):
    def printer(params, ctx):
        print("stray output from a library")
        return {"done": True}

    stdin = io.StringIO(json.dumps({"id": 1, "cmd": "printer"}) + "\n")
    stdout = io.StringIO()

    assert run_server(stdin, stdout, {"printer": printer}) == 0

    lines = stdout.getvalue().splitlines()
    assert [json.loads(line)["type"] for line in lines] == ["ready", "result"]
    assert "stray" not in stdout.getvalue()
    assert "stray output from a library" in capsys.readouterr().err
