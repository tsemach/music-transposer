from pathlib import Path

from musicxml_builder import make_musicxml, quarters, whole_rest

from backend.validate.durations import check_durations

MULTIPLE_REST = "<attributes><measure-style><multiple-rest>4</multiple-rest></measure-style></attributes>"


def findings_for(tmp_path: Path, measures: list[str], **options):
    path = tmp_path / "score.musicxml"
    path.write_text(make_musicxml(measures, **options), encoding="utf-8")
    return check_durations(path)


def test_long_middle_measure_flagged(tmp_path):
    [finding] = findings_for(tmp_path, [quarters(4), quarters(5), quarters(4)])

    assert (finding.check, finding.severity, finding.measure) == ("measure-duration", "error", "2")
    assert "5" in finding.message and "4" in finding.message


def test_short_middle_measure_flagged(tmp_path):
    [finding] = findings_for(tmp_path, [quarters(4), quarters(3), quarters(4)])

    assert finding.measure == "2"


def test_short_first_measure_pickup_not_flagged(tmp_path):
    assert findings_for(tmp_path, [quarters(1), quarters(4), quarters(4)], measure_numbers=["0", "1", "2"]) == []


def test_short_last_measure_not_flagged(tmp_path):
    assert findings_for(tmp_path, [quarters(4), quarters(4), quarters(2)]) == []


def test_multiple_rest_and_full_rest_measures_not_flagged(tmp_path):
    measures = [quarters(4), MULTIPLE_REST + whole_rest(), whole_rest(), quarters(4)]

    assert findings_for(tmp_path, measures) == []


def test_all_correct_gives_no_findings(tmp_path):
    assert findings_for(tmp_path, [quarters(3)] * 4, beats=3) == []
