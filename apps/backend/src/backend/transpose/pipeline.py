import os
import re
from dataclasses import dataclass
from pathlib import Path

from music21 import converter, instrument, stream

from ..errors import InvalidInputError, ValidationFailedError
from ..validate import validate_musicxml
from ..validate.report import ValidationReport
from .register import ChosenInterval
from .saxophones import Register, SaxophoneKind, target_of
from .transposer import transpose_score
from .written_xml import fix_for_musescore

SEMITONES_TO_KIND: dict[int, SaxophoneKind] = {-9: "alto", -14: "tenor"}
INSTRUMENT_WORDS = {"alto", "tenor", "sax", "saxophone"}


@dataclass
class TransposeOutcome:
    out_path: Path
    interval: ChosenInterval
    report: ValidationReport
    warnings: list[str]


def transpose_musicxml(
    source_path: Path,
    out_path: Path,
    source: SaxophoneKind,
    register: Register = "auto",
    force: bool = False,
    title: str | None = None,
    report: ValidationReport | None = None,
) -> TransposeOutcome:
    out_path = out_path if out_path.suffix else out_path.with_name(out_path.name + ".musicxml")
    if _is_same_file(out_path, source_path):
        raise InvalidInputError(f"Output would overwrite the input file: {source_path}")
    report = report if report is not None else validate_musicxml(source_path)
    if report.has_errors and not force:
        raise ValidationFailedError(report)

    score = converter.parse(str(source_path), format="musicxml")
    result = transpose_score(score, source, register, title or _default_title(source_path))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.score.write("musicxml", fp=str(out_path))
    fix_for_musescore(out_path)
    return TransposeOutcome(out_path, result.interval, report, _warnings(score, source, result.interval))


def _default_title(source_path: Path) -> str:
    words = re.split(r"[-_\s]+", source_path.stem)
    return " ".join(word.capitalize() for word in words if word and word.lower() not in INSTRUMENT_WORDS)


def _is_same_file(first: Path, second: Path) -> bool:
    if first.resolve() == second.resolve():
        return True
    return first.exists() and second.exists() and os.path.samefile(first, second)


def _warnings(score: stream.Score, source: SaxophoneKind, interval: ChosenInterval) -> list[str]:
    warnings = []
    declared = _declared_kind(score)
    if declared and declared != source:
        article = "an" if declared == "alto" else "a"
        warnings.append(
            f"Part is declared as {article} {declared} saxophone (name or transposition) "
            f"but the source instrument was given as {source}"
        )
    if interval.out_of_range:
        warnings.append(
            f"{interval.out_of_range} notes fall outside the written range of the "
            f"{target_of(source)} saxophone (Bb3-F6)"
        )
    return warnings


def _declared_kind(score: stream.Score) -> SaxophoneKind | None:
    instruments = list(score.recurse().getElementsByClass(instrument.Instrument))
    names = [part.partName for part in score.parts] + [item.instrumentName for item in instruments]
    text = " ".join(name for name in names if name).lower()
    kinds = {kind for kind in ("alto", "tenor") if kind in text}
    kinds |= {
        SEMITONES_TO_KIND[item.transposition.semitones]
        for item in instruments
        if item.transposition is not None and item.transposition.semitones in SEMITONES_TO_KIND
    }
    return next(iter(kinds)) if len(kinds) == 1 else None
