from dataclasses import dataclass

from music21 import harmony, interval, stream

from .saxophones import (
    WRITTEN_HIGH_PS,
    WRITTEN_LOW_PS,
    ChosenRegister,
    Register,
    SaxophoneKind,
    interval_name,
)

CANDIDATE_ORDER: tuple[ChosenRegister, ...] = ("same", "shifted")


@dataclass(frozen=True)
class ChosenInterval:
    name: str
    register: ChosenRegister
    out_of_range: int


def choose_interval(
    score: stream.Score, source: SaxophoneKind, register: Register = "auto"
) -> ChosenInterval:
    candidates = [_candidate(score, source, option) for option in CANDIDATE_ORDER]
    if register == "auto":
        return min(candidates, key=lambda candidate: candidate.out_of_range)
    return next(candidate for candidate in candidates if candidate.register == register)


def _candidate(score: stream.Score, source: SaxophoneKind, register: ChosenRegister) -> ChosenInterval:
    name = interval_name(source, register)
    return ChosenInterval(name, register, _count_out_of_range(score, interval.Interval(name).semitones))


def _count_out_of_range(score: stream.Score, semitones: int) -> int:
    played = (element for element in score.recurse().notes if not isinstance(element, harmony.Harmony))
    shifted = (pitch.ps + semitones for element in played for pitch in element.pitches)
    return sum(1 for ps in shifted if not WRITTEN_LOW_PS <= ps <= WRITTEN_HIGH_PS)
