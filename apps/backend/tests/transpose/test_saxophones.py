from music21 import pitch

from backend.transpose.saxophones import (
    WRITTEN_HIGH_PS,
    WRITTEN_LOW_PS,
    instrument_for,
    interval_name,
    part_name_for,
    target_of,
)


def test_target_of_swaps_kind():
    assert target_of("alto") == "tenor"
    assert target_of("tenor") == "alto"


def test_interval_names_for_all_four_combinations():
    assert interval_name("alto", "same") == "P4"
    assert interval_name("alto", "shifted") == "-P5"
    assert interval_name("tenor", "same") == "-P4"
    assert interval_name("tenor", "shifted") == "P5"


def test_same_sound_interval_round_trips_to_original_pitch():
    alto = pitch.Pitch("C4")

    tenor = alto.transpose(interval_name("alto", "same"))
    back = tenor.transpose(interval_name("tenor", "same"))

    assert tenor.nameWithOctave == "F4"
    assert back.nameWithOctave == "C4"


def test_instruments_carry_saxophone_transposition():
    assert instrument_for("tenor").transposition.semitones == -14
    assert instrument_for("alto").transposition.semitones == -9
    assert part_name_for("tenor") == "Tenor Saxophone"
    assert part_name_for("alto") == "Alto Saxophone"


def test_written_range_is_bb3_to_f6():
    assert WRITTEN_LOW_PS == pitch.Pitch("Bb3").ps
    assert WRITTEN_HIGH_PS == pitch.Pitch("F6").ps
