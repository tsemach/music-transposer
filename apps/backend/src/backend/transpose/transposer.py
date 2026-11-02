import copy
from dataclasses import dataclass

from music21 import instrument, key, metadata, stream

from .register import ChosenInterval, choose_interval
from .saxophones import (
    Register,
    SaxophoneKind,
    instrument_for,
    part_abbreviation_for,
    part_name_for,
    target_of,
)


@dataclass
class TransposeResult:
    score: stream.Score
    interval: ChosenInterval


def transpose_score(
    score: stream.Score,
    source: SaxophoneKind,
    register: Register = "auto",
    title: str | None = None,
) -> TransposeResult:
    working = copy.deepcopy(score)
    _ensure_initial_key_signature(working)
    chosen = choose_interval(working, source, register)
    transposed = working.transpose(chosen.name)
    _retarget_instrument(transposed, target_of(source))
    if title is not None:
        transposed.metadata = metadata.Metadata(title=title, composer="")
    return TransposeResult(transposed, chosen)


def _ensure_initial_key_signature(score: stream.Score) -> None:
    for part in score.parts:
        first = part.getElementsByClass(stream.Measure).first()
        if first is not None and first.getElementsByClass(key.KeySignature).first() is None:
            first.insert(0, key.KeySignature(0))


def _retarget_instrument(score: stream.Score, kind: SaxophoneKind) -> None:
    score.atSoundingPitch = False
    for part in score.parts:
        part.atSoundingPitch = False
        for existing in list(part.recurse().getElementsByClass(instrument.Instrument)):
            part.remove(existing, recurse=True)
        part.insert(0, instrument_for(kind))
        part.partName = part_name_for(kind)
        part.partAbbreviation = part_abbreviation_for(kind)
