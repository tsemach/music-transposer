from dataclasses import dataclass
from pathlib import Path

from music21 import converter, instrument, stream

from ..errors import InvalidInputError, ValidationFailedError
from ..validate import validate_musicxml
from ..validate.report import ValidationReport
from .register import ChosenInterval
from .saxophones import Register, SaxophoneKind, target_of
from .transposer import transpose_score


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
) -> TransposeOutcome:
    if out_path.resolve() == source_path.resolve():
        raise InvalidInputError(f"Output would overwrite the input file: {source_path}")
    report = validate_musicxml(source_path)
    if report.has_errors and not force:
        raise ValidationFailedError(report)

    score = converter.parse(str(source_path), format="musicxml")
    result = transpose_score(score, source, register)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.score.write("musicxml", fp=str(out_path))
    return TransposeOutcome(out_path, result.interval, report, _warnings(score, source, result.interval))


def _warnings(score: stream.Score, source: SaxophoneKind, interval: ChosenInterval) -> list[str]:
    warnings = []
    declared = _declared_kind(score)
    if declared and declared != source:
        warnings.append(f"Part is named for a {declared} saxophone but --from {source} was given")
    if interval.out_of_range:
        warnings.append(
            f"{interval.out_of_range} notes fall outside the written range of the "
            f"{target_of(source)} saxophone (Bb3-F6)"
        )
    return warnings


def _declared_kind(score: stream.Score) -> SaxophoneKind | None:
    names = [part.partName for part in score.parts]
    names += [item.instrumentName for item in score.recurse().getElementsByClass(instrument.Instrument)]
    text = " ".join(name for name in names if name).lower()
    kinds = [kind for kind in ("alto", "tenor") if kind in text]
    return kinds[0] if len(kinds) == 1 else None
