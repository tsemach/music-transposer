from music21 import converter, instrument, key, tie
from musicxml_builder import make_musicxml, quarters
from score_helpers import make_score

from backend.transpose.transposer import transpose_score


def first_key_sharps(score) -> int:
    return score.recurse().getElementsByClass(key.KeySignature).first().sharps


def names(score) -> list[str]:
    return [p.nameWithOctave for element in score.recurse().notes for p in element.pitches]


def test_no_key_signature_gets_transposed_one_at_bar_one():
    result = transpose_score(make_score(["C5"]), "alto", "same")

    assert first_key_sharps(result.score) == -1


def test_existing_key_signature_is_transposed():
    result = transpose_score(make_score(["Bb4"], key_fifths=-2), "alto", "same")

    assert first_key_sharps(result.score) == -3


def test_notes_transposed_by_chosen_interval_with_chords_and_ties():
    score = make_score(["C5 E5", "D5"])
    list(score.recurse().notes)[1].tie = tie.Tie("start")

    result = transpose_score(score, "alto", "same")

    assert names(result.score) == ["F5", "A5", "G5"]
    assert list(result.score.recurse().notes)[1].tie.type == "start"


def test_instrument_and_part_name_replaced_with_target():
    result = transpose_score(make_score(["C5"]), "alto", "same")

    part = result.score.parts[0]
    assert part.partName == "Tenor Saxophone"
    instruments = list(part.recurse().getElementsByClass(instrument.Instrument))
    assert [type(item) for item in instruments] == [instrument.TenorSaxophone]


def test_input_score_not_mutated():
    score = make_score(["C5", "E5"])

    transpose_score(score, "alto", "same")

    assert names(score) == ["C5", "E5"]
    assert score.recurse().getElementsByClass(key.KeySignature).first() is None


def test_alto_to_tenor_then_back_restores_pitches_and_key():
    original = make_score(["C5", "E5", "G4"], key_fifths=0)

    tenor = transpose_score(original, "alto", "same").score
    alto = transpose_score(tenor, "tenor", "same").score

    assert names(alto) == ["C5", "E5", "G4"]
    assert first_key_sharps(alto) == 0


def test_written_musicxml_declares_target_transposition(tmp_path):
    result = transpose_score(make_score(["C5"]), "alto", "same")
    path = tmp_path / "tenor.musicxml"

    result.score.write("musicxml", fp=str(path))

    xml = path.read_text(encoding="utf-8")
    assert "<chromatic>-2</chromatic>" in xml
    assert "<octave-change>-1</octave-change>" in xml


def test_written_pitches_survive_export_of_a_score_parsed_from_file(tmp_path):
    source = tmp_path / "in.musicxml"
    source.write_text(make_musicxml([quarters(4)]), encoding="utf-8")
    parsed = converter.parse(str(source), format="musicxml")
    out = tmp_path / "out.musicxml"

    transpose_score(parsed, "alto", "same").score.write("musicxml", fp=str(out))

    assert names(converter.parse(str(out)))[0] == "F4"


def test_part_abbreviation_replaced_with_target():
    result = transpose_score(make_score(["C5"]), "alto", "same")

    assert result.score.parts[0].partAbbreviation == "T. Sax."
