import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .convert import convert_pdf
from .enrich import enrich_musicxml
from .errors import CancelledError, ValidationFailedError
from .musescore_locator import find_musescore
from .render import render_pdf
from .transpose.pipeline import transpose_musicxml
from .transpose.register import ChosenInterval
from .transpose.saxophones import Register, SaxophoneKind, target_of
from .validate import validate_musicxml
from .validate.report import ValidationReport

ProgressCallback = Callable[[str, int], None]


@dataclass
class PipelineResult:
    original_musicxml: Path
    tenor_musicxml: Path
    pdf: Path
    interval: ChosenInterval
    report: ValidationReport
    warnings: list[str]


def run_pipeline(
    pdf: Path,
    out_dir: Path,
    source: SaxophoneKind,
    register: Register = "auto",
    force: bool = False,
    audiveris: Path | None = None,
    musescore: Path | None = None,
    on_progress: ProgressCallback | None = None,
    cancel: threading.Event | None = None,
) -> PipelineResult:
    progress = on_progress or (lambda stage, pct: None)
    musescore_path = find_musescore(musescore)

    progress("omr", 5)
    movements = convert_pdf(pdf, out_dir, audiveris, cancel)
    original = movements[0]
    warnings = [f"OMR produced {len(movements)} movements; only the first was used"] if len(movements) > 1 else []
    _raise_if_cancelled(cancel)

    progress("validate", 55)
    report = validate_musicxml(original)
    if report.has_errors and not force:
        raise ValidationFailedError(report)
    _raise_if_cancelled(cancel)

    progress("transpose", 65)
    warnings += enrich_musicxml(pdf, original)
    target = target_of(source)
    transposed_path = out_dir / f"{pdf.stem}.{target}.musicxml"
    outcome = transpose_musicxml(original, transposed_path, source, register, force=True, report=report)
    _raise_if_cancelled(cancel)

    progress("render", 80)
    pdf_path = render_pdf(transposed_path, out_dir / f"{pdf.stem}.{target}.pdf", musescore_path, cancel=cancel)

    progress("done", 100)
    return PipelineResult(original, transposed_path, pdf_path, outcome.interval, report, warnings + outcome.warnings)


def _raise_if_cancelled(cancel: threading.Event | None) -> None:
    if cancel is not None and cancel.is_set():
        raise CancelledError("Cancelled")
