import shutil
import threading
import time
from pathlib import Path

import pytest

from backend.errors import CancelledError, InvalidInputError, RenderFailedError
from backend.render import render_pdf

FAKE = Path(__file__).parent / "fake_musescore.py"


def install_fake(directory: Path, name: str = "mscore") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    executable = directory / name
    shutil.copy(FAKE, executable)
    executable.chmod(0o755)
    return executable


@pytest.fixture
def musescore(tmp_path) -> Path:
    return install_fake(tmp_path / "bin")


@pytest.fixture
def score(tmp_path) -> Path:
    path = tmp_path / "score.musicxml"
    path.write_text("<score-partwise/>", encoding="utf-8")
    return path


def test_writes_pdf_and_returns_path(tmp_path, musescore, score):
    out = tmp_path / "out" / "score.pdf"

    result = render_pdf(score, out, musescore)

    assert result == out
    assert out.read_bytes().startswith(b"%PDF")


def test_nonzero_exit_raises_with_stderr(monkeypatch, tmp_path, musescore, score):
    monkeypatch.setenv("FAKE_MODE", "fail")

    with pytest.raises(RenderFailedError) as raised:
        render_pdf(score, tmp_path / "score.pdf", musescore)

    assert raised.value.returncode == 4
    assert "bad score" in raised.value.stderr


def test_exit_zero_without_pdf_raises(monkeypatch, tmp_path, musescore, score):
    monkeypatch.setenv("FAKE_MODE", "none")

    with pytest.raises(RenderFailedError, match="no PDF"):
        render_pdf(score, tmp_path / "score.pdf", musescore)


def test_stale_pdf_not_accepted(monkeypatch, tmp_path, musescore, score):
    out = tmp_path / "score.pdf"
    out.write_bytes(b"%PDF old")
    monkeypatch.setenv("FAKE_MODE", "none")

    with pytest.raises(RenderFailedError):
        render_pdf(score, out, musescore)

    assert not out.exists()


def test_missing_musicxml_raises_before_launching(monkeypatch, tmp_path, musescore):
    args_file = tmp_path / "args.txt"
    monkeypatch.setenv("FAKE_ARGS_FILE", str(args_file))

    with pytest.raises(InvalidInputError):
        render_pdf(tmp_path / "absent.musicxml", tmp_path / "x.pdf", musescore)

    assert not args_file.exists()


def test_non_pdf_output_name_raises(tmp_path, musescore, score):
    with pytest.raises(InvalidInputError):
        render_pdf(score, tmp_path / "score.png", musescore)


def test_path_with_spaces_and_hebrew_name(tmp_path, musescore):
    score = tmp_path / "my folder" / "שיר.musicxml"
    score.parent.mkdir()
    score.write_text("<score-partwise/>", encoding="utf-8")

    result = render_pdf(score, tmp_path / "תוצאה" / "שיר.pdf", musescore)

    assert result.is_file()


def test_appimage_name_adds_extract_and_run_flag(monkeypatch, tmp_path, score):
    appimage = install_fake(tmp_path / "apps", "MuseScore.AppImage")
    args_file = tmp_path / "args.txt"
    monkeypatch.setenv("FAKE_ARGS_FILE", str(args_file))

    render_pdf(score, tmp_path / "score.pdf", appimage)

    assert args_file.read_text(encoding="utf-8").splitlines()[0] == "--appimage-extract-and-run"


def test_cancel_raises_cancelled(monkeypatch, tmp_path, musescore, score):
    monkeypatch.setenv("FAKE_MODE", "sleep")
    cancel = threading.Event()
    threading.Timer(0.4, cancel.set).start()
    started = time.monotonic()

    with pytest.raises(CancelledError):
        render_pdf(score, tmp_path / "score.pdf", musescore, cancel=cancel)

    assert time.monotonic() - started < 10
