import os

import pytest
from music21 import converter
from musicxml_builder import make_musicxml, quarters

from backend.errors import InvalidInputError, ValidationFailedError
from backend.transpose.pipeline import transpose_musicxml

ORPHAN_ENDING = '<barline location="left"><ending number="1" type="start"/></barline>'


def high_notes() -> str:
    note = "<note><pitch><step>D</step><octave>6</octave></pitch><duration>1</duration><type>quarter</type></note>"
    return note * 4


def write_score(tmp_path, measures, name="in.musicxml", xml_edit=lambda xml: xml):
    path = tmp_path / name
    path.write_text(xml_edit(make_musicxml(measures)), encoding="utf-8")
    return path


def test_clean_file_is_written_and_parses(tmp_path):
    source = write_score(tmp_path, [quarters(4)] * 3)

    outcome = transpose_musicxml(source, tmp_path / "out.musicxml", "alto")

    assert outcome.out_path.is_file()
    assert (outcome.interval.register, outcome.report.findings, outcome.warnings) == ("same", [], [])
    first_note = converter.parse(str(outcome.out_path)).recurse().notes.first()
    assert first_note.pitches[0].nameWithOctave == "F4"


def test_validation_errors_refuse_and_write_nothing(tmp_path):
    source = write_score(tmp_path, [quarters(4), "", quarters(4)])
    out = tmp_path / "out.musicxml"

    with pytest.raises(ValidationFailedError) as raised:
        transpose_musicxml(source, out, "alto")

    assert not out.exists()
    assert "empty-measure" in str(raised.value)
    assert raised.value.report.has_errors


def test_force_converts_despite_errors(tmp_path):
    source = write_score(tmp_path, [quarters(4), "", quarters(4)])

    outcome = transpose_musicxml(source, tmp_path / "out.musicxml", "alto", force=True)

    assert outcome.out_path.is_file()
    assert outcome.report.has_errors


def test_warnings_only_does_not_block(tmp_path):
    source = write_score(tmp_path, [quarters(4), ORPHAN_ENDING + quarters(4)])

    outcome = transpose_musicxml(source, tmp_path / "out.musicxml", "alto")

    assert outcome.out_path.is_file()
    assert [finding.check for finding in outcome.report.warnings] == ["orphan-ending"]


def test_output_equal_to_input_refused(tmp_path):
    source = write_score(tmp_path, [quarters(4)])

    with pytest.raises(InvalidInputError):
        transpose_musicxml(source, tmp_path / "." / "in.musicxml", "alto")

    assert "<step>C</step>" in source.read_text(encoding="utf-8")


def test_out_of_range_count_reported_as_warning(tmp_path):
    source = write_score(tmp_path, [high_notes()])

    outcome = transpose_musicxml(source, tmp_path / "out.musicxml", "alto", register="same")

    assert outcome.interval.out_of_range == 4
    assert any("4 notes" in warning and "range" in warning for warning in outcome.warnings)


def test_part_named_tenor_with_from_alto_warns(tmp_path):
    source = write_score(
        tmp_path,
        [quarters(4)],
        xml_edit=lambda xml: xml.replace("<part-name>Test</part-name>", "<part-name>Tenor Saxophone</part-name>"),
    )

    outcome = transpose_musicxml(source, tmp_path / "out.musicxml", "alto")

    assert any("declared as a tenor" in warning for warning in outcome.warnings)


def test_part_named_alto_with_from_tenor_warns(tmp_path):
    source = write_score(
        tmp_path,
        [quarters(4)],
        xml_edit=lambda xml: xml.replace("<part-name>Test</part-name>", "<part-name>Alto Sax</part-name>"),
    )

    outcome = transpose_musicxml(source, tmp_path / "out.musicxml", "tenor")

    assert any("declared as an alto" in warning for warning in outcome.warnings)


TENOR_TRANSPOSE = (
    "<transpose><diatonic>-1</diatonic><chromatic>-2</chromatic>"
    "<octave-change>-1</octave-change></transpose>"
)


def test_transposition_tag_conflicting_with_from_warns_even_without_a_name(tmp_path):
    path = tmp_path / "in.musicxml"
    path.write_text(make_musicxml([quarters(4)], first_attributes=TENOR_TRANSPOSE), encoding="utf-8")

    outcome = transpose_musicxml(path, tmp_path / "out.musicxml", "alto")

    assert any("declared as a tenor" in warning for warning in outcome.warnings)


def test_output_without_extension_gets_musicxml_suffix(tmp_path):
    source = write_score(tmp_path, [quarters(4)])

    outcome = transpose_musicxml(source, tmp_path / "result", "alto")

    assert outcome.out_path == tmp_path / "result.musicxml"
    assert outcome.out_path.is_file()


def test_extensionless_output_that_resolves_to_input_is_refused(tmp_path):
    source = write_score(tmp_path, [quarters(4)], name="song.musicxml")

    with pytest.raises(InvalidInputError):
        transpose_musicxml(source, tmp_path / "song", "alto")

    assert "<step>C</step>" in source.read_text(encoding="utf-8")


def test_hard_link_to_input_is_refused(tmp_path):
    source = write_score(tmp_path, [quarters(4)])
    link = tmp_path / "link.musicxml"
    try:
        os.link(source, link)
    except OSError:
        pytest.skip("hard links not supported here")

    with pytest.raises(InvalidInputError):
        transpose_musicxml(source, link, "alto")

    assert "<step>C</step>" in source.read_text(encoding="utf-8")
