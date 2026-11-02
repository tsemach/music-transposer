import os
import shutil
import threading
import time
from pathlib import Path

import pytest

from backend.errors import CancelledError, InvalidInputError, NoOutputError, OmrFailedError
from backend.omr import run_omr

FAKE = Path(__file__).parent / "fake_audiveris.py"


@pytest.fixture
def audiveris(tmp_path) -> Path:
    executable = tmp_path / "bin" / "Audiveris"
    executable.parent.mkdir()
    shutil.copy(FAKE, executable)
    executable.chmod(0o755)
    return executable


@pytest.fixture
def pdf(tmp_path) -> Path:
    path = tmp_path / "sheet.pdf"
    path.write_bytes(b"%PDF-1.4")
    return path


def test_returns_mxl_files_sorted(monkeypatch, tmp_path, audiveris, pdf):
    monkeypatch.setenv("FAKE_MODE", "two")

    result = run_omr(pdf, tmp_path / "out", audiveris)

    assert [p.name for p in result] == ["sheet.mvt2.mxl", "sheet.mxl"]


def test_nonzero_exit_raises_with_stderr(monkeypatch, tmp_path, audiveris, pdf):
    monkeypatch.setenv("FAKE_MODE", "fail")

    with pytest.raises(OmrFailedError) as raised:
        run_omr(pdf, tmp_path / "out", audiveris)

    assert raised.value.returncode == 3
    assert "boom" in raised.value.stderr


def test_exit_zero_without_output_raises_no_output(monkeypatch, tmp_path, audiveris, pdf):
    monkeypatch.setenv("FAKE_MODE", "none")

    with pytest.raises(NoOutputError):
        run_omr(pdf, tmp_path / "out", audiveris)


def test_timeout_kills_process_and_raises(monkeypatch, tmp_path, audiveris, pdf):
    monkeypatch.setenv("FAKE_MODE", "sleep")
    started = time.monotonic()

    with pytest.raises(OmrFailedError, match="timed out"):
        run_omr(pdf, tmp_path / "out", audiveris, timeout_s=1)

    assert time.monotonic() - started < 10


def test_missing_pdf_raises_before_launching(monkeypatch, tmp_path, audiveris):
    args_file = tmp_path / "args.txt"
    monkeypatch.setenv("FAKE_ARGS_FILE", str(args_file))

    with pytest.raises(InvalidInputError):
        run_omr(tmp_path / "absent.pdf", tmp_path / "out", audiveris)

    assert not args_file.exists()


def test_non_pdf_extension_raises(tmp_path, audiveris):
    text = tmp_path / "notes.txt"
    text.write_text("x")

    with pytest.raises(InvalidInputError):
        run_omr(text, tmp_path / "out", audiveris)


def test_path_with_spaces_and_hebrew_name_is_passed_intact(monkeypatch, tmp_path, audiveris):
    pdf = tmp_path / "my folder" / "שיר ראשון.pdf"
    pdf.parent.mkdir()
    pdf.write_bytes(b"%PDF-1.4")
    args_file = tmp_path / "args.txt"
    monkeypatch.setenv("FAKE_ARGS_FILE", str(args_file))

    result = run_omr(pdf, tmp_path / "out", audiveris)

    assert args_file.read_text(encoding="utf-8").splitlines()[-1] == str(pdf)
    assert result[0].name == "שיר ראשון.mxl"


def test_stale_mxl_from_previous_run_not_returned(monkeypatch, tmp_path, audiveris, pdf):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    stale = out_dir / "old.mxl"
    stale.write_bytes(b"old")
    os.utime(stale, (1, 1))
    monkeypatch.setenv("FAKE_MODE", "one")

    result = run_omr(pdf, out_dir, audiveris)

    assert [p.name for p in result] == ["sheet.mxl"]


def test_stale_mxl_alone_does_not_count_as_output(monkeypatch, tmp_path, audiveris, pdf):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "sheet.mxl").write_bytes(b"old")
    monkeypatch.setenv("FAKE_MODE", "none")

    with pytest.raises(NoOutputError):
        run_omr(pdf, out_dir, audiveris)


def test_cancel_kills_audiveris_and_raises_cancelled(monkeypatch, tmp_path, audiveris, pdf):
    monkeypatch.setenv("FAKE_MODE", "sleep")
    cancel = threading.Event()
    threading.Timer(0.5, cancel.set).start()
    started = time.monotonic()

    with pytest.raises(CancelledError):
        run_omr(pdf, tmp_path / "out", audiveris, cancel=cancel)

    assert time.monotonic() - started < 10
