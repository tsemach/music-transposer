from pathlib import Path

from music21 import converter, meter, stream

from .report import Finding

TOLERANCE = 1e-6


def check_durations(path: Path) -> list[Finding]:
    score = converter.parse(str(path))
    if not score.parts:
        return []
    measures = list(score.parts[0].getElementsByClass(stream.Measure))
    findings = []
    for index, measure in enumerate(measures):
        time_signature = measure.timeSignature or measure.getContextByClass(meter.TimeSignature)
        if time_signature is None:
            continue
        expected = float(time_signature.barDuration.quarterLength)
        found = float(measure.highestTime)
        is_edge = index in (0, len(measures) - 1)
        too_long = found > expected + TOLERANCE
        too_short = found < expected - TOLERANCE and not is_edge
        if too_long or too_short:
            findings.append(
                Finding(
                    "measure-duration",
                    "error",
                    f"{measure.number}{measure.numberSuffix or ''}",
                    f"measure lasts {found:g} quarter notes, time signature expects {expected:g}",
                )
            )
    return findings
