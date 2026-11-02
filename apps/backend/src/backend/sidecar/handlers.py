import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..audiveris_locator import find_audiveris
from ..errors import (
    BackendError,
    CancelledError,
    ExecutableNotFoundError,
    InvalidInputError,
    ValidationFailedError,
)
from ..musescore_locator import find_musescore
from ..pipeline import run_pipeline
from ..validate import validate_musicxml
from ..validate.report import Finding


@dataclass
class RequestContext:
    progress: Callable[[str, int], None]
    cancel: threading.Event


Handler = Callable[[dict, RequestContext], dict]


def doctor(params: dict, ctx: RequestContext) -> dict:
    return {
        "audiveris": _locate(find_audiveris, params.get("audiveris")),
        "musescore": _locate(find_musescore, params.get("musescore")),
    }


def validate(params: dict, ctx: RequestContext) -> dict:
    report = validate_musicxml(Path(_require(params, "musicxml")))
    return {"findings": [_finding_dict(finding) for finding in report.findings]}


def pipeline(params: dict, ctx: RequestContext) -> dict:
    pdf = Path(_require(params, "pdf"))
    source = _require(params, "source")
    out_dir = Path(params["outDir"]) if params.get("outDir") else pdf.parent / pdf.stem
    outcome = run_pipeline(
        pdf,
        out_dir,
        source,
        params.get("register", "auto"),
        bool(params.get("force", False)),
        _optional_path(params.get("audiveris")),
        _optional_path(params.get("musescore")),
        on_progress=ctx.progress,
        cancel=ctx.cancel,
    )
    return {
        "originalMusicxml": str(outcome.original_musicxml),
        "tenorMusicxml": str(outcome.tenor_musicxml),
        "pdf": str(outcome.pdf),
        "interval": {
            "name": outcome.interval.name,
            "register": outcome.interval.register,
            "outOfRange": outcome.interval.out_of_range,
        },
        "findings": [_finding_dict(finding) for finding in outcome.report.findings],
        "warnings": outcome.warnings,
    }


HANDLERS: dict[str, Handler] = {"doctor": doctor, "validate": validate, "pipeline": pipeline}


def classify(error: Exception) -> tuple[str, str, dict | None]:
    message = str(error)
    if isinstance(error, ValidationFailedError):
        return "validation_failed", message, {"findings": [_finding_dict(f) for f in error.report.findings]}
    if isinstance(error, CancelledError):
        return "cancelled", message, None
    if isinstance(error, ExecutableNotFoundError):
        return "tool_not_found", message, None
    if isinstance(error, InvalidInputError):
        return "invalid_input", message, None
    if isinstance(error, BackendError):
        return "failed", message, None
    return "internal", message, None


def _locate(finder: Callable[[Path | None], Path], override: str | None) -> str | None:
    try:
        return str(finder(_optional_path(override)))
    except ExecutableNotFoundError:
        return None


def _optional_path(value: str | None) -> Path | None:
    return Path(value) if value else None


def _require(params: dict, key: str) -> str:
    value = params.get(key)
    if not value:
        raise InvalidInputError(f"Missing parameter: {key}")
    return value


def _finding_dict(finding: Finding) -> dict:
    return {
        "check": finding.check,
        "severity": finding.severity,
        "measure": finding.measure,
        "message": finding.message,
    }
