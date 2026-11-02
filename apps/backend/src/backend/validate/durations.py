from pathlib import Path
from xml.etree import ElementTree

from music21 import converter, meter, stream
from music21.exceptions21 import Music21Exception

from ..errors import InvalidInputError
from .report import Finding

TOLERANCE = 1e-6

MeasureRow = tuple[str, float, float]


def check_durations(path: Path) -> list[Finding]:
    rows = _measure_rows(path)
    return [
        Finding(
            "measure-duration",
            "error",
            label,
            f"measure lasts {found:g} quarter notes, time signature expects {expected:g}",
        )
        for index, (label, found, expected) in enumerate(rows)
        if _is_wrong_length(rows, index)
    ]


def _is_wrong_length(rows: list[MeasureRow], index: int) -> bool:
    _, found, expected = rows[index]
    if found > expected + TOLERANCE:
        return True
    if found >= expected - TOLERANCE or index in (0, len(rows) - 1):
        return False
    neighbours = (rows[index - 1][1], rows[index + 1][1])
    return not any(abs(found + other - expected) <= TOLERANCE for other in neighbours)


def _measure_rows(path: Path) -> list[MeasureRow]:
    try:
        score = converter.parse(str(path), format="musicxml")
    except Music21Exception as error:
        raise InvalidInputError(f"{path} is not readable MusicXML: {error}") from error
    if not score.parts:
        return []
    measures = list(score.parts[0].getElementsByClass(stream.Measure))
    labels = _xml_labels(path, len(measures))
    rows = []
    for label, measure in zip(labels, measures):
        time_signature = measure.timeSignature or measure.getContextByClass(meter.TimeSignature)
        if time_signature is not None:
            rows.append((label or str(measure.number), float(measure.highestTime), float(time_signature.barDuration.quarterLength)))
    return rows


def _xml_labels(path: Path, expected_count: int) -> list[str | None]:
    part = ElementTree.parse(path).getroot().find("part")
    labels = [measure.get("number") for measure in part.findall("measure")] if part is not None else []
    return labels if len(labels) == expected_count else [None] * expected_count
