import pytest
from musicxml_builder import make_musicxml, quarters

from backend.errors import InvalidInputError
from backend.validate import validate_musicxml


def test_validate_missing_file_raises_invalid_input(tmp_path):
    with pytest.raises(InvalidInputError):
        validate_musicxml(tmp_path / "absent.musicxml")


def test_validate_non_xml_raises_invalid_input(tmp_path):
    path = tmp_path / "garbage.musicxml"
    path.write_text("this is not xml", encoding="utf-8")

    with pytest.raises(InvalidInputError):
        validate_musicxml(path)


def test_validate_well_formed_non_musicxml_raises_invalid_input(tmp_path):
    path = tmp_path / "other.musicxml"
    path.write_text("<foo/>", encoding="utf-8")

    with pytest.raises(InvalidInputError):
        validate_musicxml(path)


def test_validate_accepts_musicxml_regardless_of_file_extension(tmp_path):
    path = tmp_path / "score.txt"
    path.write_text(make_musicxml([quarters(4), quarters(4)]), encoding="utf-8")

    assert validate_musicxml(path).findings == []


def test_validate_combines_structure_and_duration_findings(tmp_path):
    path = tmp_path / "score.musicxml"
    path.write_text(make_musicxml([quarters(4), "", quarters(5), quarters(4)]), encoding="utf-8")

    report = validate_musicxml(path)

    found = {(finding.check, finding.measure) for finding in report.findings}
    assert ("empty-measure", "2") in found
    assert ("measure-duration", "3") in found
