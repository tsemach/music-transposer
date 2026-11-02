from typing import Literal

from music21 import instrument, pitch

SaxophoneKind = Literal["alto", "tenor"]
Register = Literal["auto", "same", "shifted"]
ChosenRegister = Literal["same", "shifted"]

WRITTEN_LOW_PS = pitch.Pitch("Bb3").ps
WRITTEN_HIGH_PS = pitch.Pitch("F6").ps

INTERVALS: dict[SaxophoneKind, dict[ChosenRegister, str]] = {
    "alto": {"same": "P4", "shifted": "-P5"},
    "tenor": {"same": "-P4", "shifted": "P5"},
}

PART_NAMES: dict[SaxophoneKind, str] = {"alto": "Alto Saxophone", "tenor": "Tenor Saxophone"}
PART_ABBREVIATIONS: dict[SaxophoneKind, str] = {"alto": "A. Sax.", "tenor": "T. Sax."}


def target_of(source: SaxophoneKind) -> SaxophoneKind:
    return "tenor" if source == "alto" else "alto"


def interval_name(source: SaxophoneKind, register: ChosenRegister) -> str:
    return INTERVALS[source][register]


def instrument_for(kind: SaxophoneKind) -> instrument.Instrument:
    return instrument.AltoSaxophone() if kind == "alto" else instrument.TenorSaxophone()


def part_name_for(kind: SaxophoneKind) -> str:
    return PART_NAMES[kind]


def part_abbreviation_for(kind: SaxophoneKind) -> str:
    return PART_ABBREVIATIONS[kind]
