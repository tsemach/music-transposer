import subprocess
import sys
import threading
import time

import pytest

from backend.errors import CancelledError
from backend.process import run_process


def python(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def test_returns_exit_code_and_stderr():
    result = run_process(python("import sys; print('oops', file=sys.stderr); sys.exit(3)"), timeout_s=10)

    assert result.returncode == 3
    assert "oops" in result.stderr


def test_timeout_kills_child_and_raises():
    started = time.monotonic()

    with pytest.raises(subprocess.TimeoutExpired):
        run_process(python("import time; time.sleep(30)"), timeout_s=1)

    assert time.monotonic() - started < 10


def test_cancel_during_run_kills_child_and_raises_cancelled():
    cancel = threading.Event()
    threading.Timer(0.3, cancel.set).start()
    started = time.monotonic()

    with pytest.raises(CancelledError):
        run_process(python("import time; time.sleep(30)"), timeout_s=60, cancel=cancel)

    assert time.monotonic() - started < 5


def test_cancel_set_before_start_never_launches(tmp_path):
    marker = tmp_path / "launched"
    cancel = threading.Event()
    cancel.set()

    with pytest.raises(CancelledError):
        run_process(python(f"open({str(marker)!r}, 'w').close()"), timeout_s=10, cancel=cancel)

    assert not marker.exists()


def test_env_is_passed_to_child():
    result = run_process(python("import os, sys; sys.exit(int(os.environ['PROBE']))"), timeout_s=10, env={"PROBE": "7"})

    assert result.returncode == 7


def test_large_output_does_not_deadlock():
    result = run_process(python("import sys; sys.stdout.write('x' * 2_000_000)"), timeout_s=20)

    assert result.returncode == 0
