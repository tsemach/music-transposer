import threading
from pathlib import Path

import pytest

from backend.errors import (
    AudiverisNotFoundError,
    BackendError,
    CancelledError,
    InvalidInputError,
    MuseScoreNotFoundError,
    ValidationFailedError,
)
from backend.pipeline import PipelineResult
from backend.sidecar import handlers
from backend.sidecar.handlers import HANDLERS, RequestContext, classify
from backend.transpose.register import ChosenInterval
from backend.validate.report import Finding, ValidationReport

FINDING = Finding("empty-measure", "error", "34", "no notes")
FINDING_DICT = {"check": "empty-measure", "severity": "error", "measure": "34", "message": "no notes"}


def context(progress=None) -> RequestContext:
    return RequestContext(progress or (lambda stage, pct: None), threading.Event())


def pipeline_result() -> PipelineResult:
    return PipelineResult(
        Path("/o/a.musicxml"),
        Path("/o/a.tenor.musicxml"),
        Path("/o/a.tenor.pdf"),
        ChosenInterval("P4", "same", 2),
        ValidationReport([FINDING]),
        ["careful"],
    )


def test_doctor_reports_found_and_missing_tools(monkeypatch):
    def missing(override=None):
        raise MuseScoreNotFoundError("nope")

    monkeypatch.setattr(handlers, "find_audiveris", lambda override=None: Path("/x/Audiveris"))
    monkeypatch.setattr(handlers, "find_musescore", missing)

    assert HANDLERS["doctor"]({}, context()) == {"audiveris": "/x/Audiveris", "musescore": None}


def test_doctor_passes_overrides(monkeypatch):
    seen = {}
    monkeypatch.setattr(handlers, "find_audiveris", lambda override=None: seen.update(a=override) or Path("/a"))
    monkeypatch.setattr(handlers, "find_musescore", lambda override=None: seen.update(m=override) or Path("/m"))

    HANDLERS["doctor"]({"audiveris": "/custom/a", "musescore": "/custom/m"}, context())

    assert seen == {"a": Path("/custom/a"), "m": Path("/custom/m")}


def test_validate_returns_findings_as_dicts(monkeypatch):
    monkeypatch.setattr(handlers, "validate_musicxml", lambda path: ValidationReport([FINDING]))

    assert HANDLERS["validate"]({"musicxml": "/o/a.musicxml"}, context()) == {"findings": [FINDING_DICT]}


def test_pipeline_maps_params_and_returns_camel_case_result(monkeypatch):
    seen = {}

    def fake(pdf, out_dir, source, register, force, audiveris, musescore, on_progress, cancel):
        seen.update(pdf=pdf, out_dir=out_dir, source=source, register=register, force=force, audiveris=audiveris)
        return pipeline_result()

    monkeypatch.setattr(handlers, "run_pipeline", fake)
    params = {"pdf": "/s/a.pdf", "source": "alto", "register": "shifted", "force": True, "outDir": "/out", "audiveris": "/a"}

    reply = HANDLERS["pipeline"](params, context())

    assert seen == {
        "pdf": Path("/s/a.pdf"), "out_dir": Path("/out"), "source": "alto",
        "register": "shifted", "force": True, "audiveris": Path("/a"),
    }
    assert reply == {
        "originalMusicxml": "/o/a.musicxml",
        "tenorMusicxml": "/o/a.tenor.musicxml",
        "pdf": "/o/a.tenor.pdf",
        "interval": {"name": "P4", "register": "same", "outOfRange": 2},
        "findings": [FINDING_DICT],
        "warnings": ["careful"],
    }


def test_pipeline_defaults_out_dir_beside_pdf(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        handlers, "run_pipeline", lambda *args, **kwargs: seen.update(out_dir=args[1], register=args[3], force=args[4]) or pipeline_result()
    )

    HANDLERS["pipeline"]({"pdf": "/songs/a.pdf", "source": "tenor"}, context())

    assert (seen["out_dir"], seen["register"], seen["force"]) == (Path("/songs/a"), "auto", False)


def test_pipeline_forwards_progress(monkeypatch):
    def fake(*args, on_progress, **kwargs):
        on_progress("omr", 5)
        return pipeline_result()

    monkeypatch.setattr(handlers, "run_pipeline", fake)
    stages = []

    HANDLERS["pipeline"]({"pdf": "/s/a.pdf", "source": "alto"}, context(lambda stage, pct: stages.append((stage, pct))))

    assert stages == [("omr", 5)]


def test_missing_required_param_is_invalid_input():
    with pytest.raises(InvalidInputError, match="pdf"):
        HANDLERS["pipeline"]({"source": "alto"}, context())


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (CancelledError("stop"), "cancelled"),
        (AudiverisNotFoundError("no audiveris"), "tool_not_found"),
        (InvalidInputError("bad"), "invalid_input"),
        (BackendError("other"), "failed"),
        (RuntimeError("kaboom"), "internal"),
    ],
)
def test_classify_codes(error, code):
    assert classify(error) == (code, str(error), None)


def test_classify_validation_failure_carries_findings():
    code, message, details = classify(ValidationFailedError(ValidationReport([FINDING])))

    assert code == "validation_failed"
    assert "empty-measure" in message
    assert details == {"findings": [FINDING_DICT]}
