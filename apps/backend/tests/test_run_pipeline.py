import threading
from pathlib import Path

import pytest
from musicxml_builder import make_musicxml, quarters

from backend import pipeline
from backend.errors import CancelledError, ValidationFailedError


@pytest.fixture
def stubs(monkeypatch, tmp_path):
    calls = {"render": 0}

    def write_musicxml(measures):
        def fake_convert(pdf, out_dir, audiveris=None, cancel=None):
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / f"{pdf.stem}.musicxml"
            path.write_text(make_musicxml(measures), encoding="utf-8")
            return [path]

        return fake_convert

    def fake_render(musicxml, out_pdf, musescore, timeout_s=120, cancel=None):
        calls["render"] += 1
        out_pdf.write_bytes(b"%PDF-1.4 fake")
        return out_pdf

    monkeypatch.setattr(pipeline, "convert_pdf", write_musicxml([quarters(4)] * 2))
    monkeypatch.setattr(pipeline, "find_musescore", lambda override=None: Path("/fake/mscore"))
    monkeypatch.setattr(pipeline, "render_pdf", fake_render)
    return type("Stubs", (), {"calls": calls, "write_musicxml": staticmethod(write_musicxml), "monkeypatch": monkeypatch})


def run(tmp_path, **options):
    stages = []
    result = pipeline.run_pipeline(
        tmp_path / "song-alto.pdf", tmp_path / "out", "alto", on_progress=lambda s, p: stages.append((s, p)), **options
    )
    return result, stages


def test_stages_reported_in_order(stubs, tmp_path):
    _, stages = run(tmp_path)

    assert stages == [("omr", 5), ("validate", 55), ("transpose", 65), ("render", 80), ("done", 100)]


def test_paths_named_after_stem_and_target(stubs, tmp_path):
    result, _ = run(tmp_path)

    out = tmp_path / "out"
    assert result.original_musicxml == out / "song-alto.musicxml"
    assert result.tenor_musicxml == out / "song-alto.tenor.musicxml"
    assert result.pdf == out / "song-alto.tenor.pdf"
    assert result.pdf.is_file() and result.interval.register == "same"


def test_validation_failure_stops_before_render(stubs, tmp_path):
    stubs.monkeypatch.setattr(pipeline, "convert_pdf", stubs.write_musicxml([quarters(4), "", quarters(4)]))

    with pytest.raises(ValidationFailedError):
        run(tmp_path)

    assert stubs.calls["render"] == 0


def test_force_continues_past_validation_errors(stubs, tmp_path):
    stubs.monkeypatch.setattr(pipeline, "convert_pdf", stubs.write_musicxml([quarters(4), "", quarters(4)]))

    result, _ = run(tmp_path, force=True)

    assert result.report.has_errors and result.pdf.is_file()


def test_extra_movements_add_warning(stubs, tmp_path):
    original = stubs.write_musicxml([quarters(4)] * 2)

    def two_movements(pdf, out_dir, audiveris=None, cancel=None):
        first = original(pdf, out_dir)[0]
        second = out_dir / f"{pdf.stem}.mvt2.musicxml"
        second.write_text(first.read_text(encoding="utf-8"), encoding="utf-8")
        return [first, second]

    stubs.monkeypatch.setattr(pipeline, "convert_pdf", two_movements)

    result, _ = run(tmp_path)

    assert any("movement" in warning for warning in result.warnings)


def test_cancel_between_stages_raises_cancelled(stubs, tmp_path):
    cancel = threading.Event()
    original = stubs.write_musicxml([quarters(4)] * 2)

    def cancelling_convert(pdf, out_dir, audiveris=None, cancel=None):
        paths = original(pdf, out_dir)
        cancel_event.set()
        return paths

    cancel_event = cancel
    stubs.monkeypatch.setattr(pipeline, "convert_pdf", cancelling_convert)

    with pytest.raises(CancelledError):
        run(tmp_path, cancel=cancel)

    assert stubs.calls["render"] == 0
