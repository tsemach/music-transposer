from xml.etree import ElementTree

from musicxml_builder import make_musicxml, quarters, whole_rest

from backend.validate.structure import check_structure


def findings_for(xml: str, check: str):
    root = ElementTree.fromstring(xml)
    return [finding for finding in check_structure(root) if finding.check == check]


def test_empty_measure_flagged_with_its_label():
    xml = make_musicxml([quarters(4), "", quarters(4)])

    [finding] = findings_for(xml, "empty-measure")

    assert (finding.severity, finding.measure) == ("error", "2")


def test_full_measure_rest_is_not_empty():
    assert findings_for(make_musicxml([whole_rest(), quarters(4)]), "empty-measure") == []


def test_multiple_rest_measure_is_not_empty():
    xml = make_musicxml(
        ["", quarters(4)],
        first_attributes="<measure-style><multiple-rest>4</multiple-rest></measure-style>",
    )

    assert findings_for(xml, "empty-measure") == []


def test_non_numeric_measure_label_preserved():
    xml = make_musicxml(["", quarters(4), ""], measure_numbers=["0", "1", "X1"])

    labels = [finding.measure for finding in findings_for(xml, "empty-measure")]

    assert labels == ["0", "X1"]


def test_missing_time_signature_flagged():
    xml = make_musicxml([quarters(4)], include_time=False)

    [finding] = findings_for(xml, "missing-time-signature")

    assert (finding.severity, finding.measure) == ("error", None)


def test_two_parts_gives_warning():
    xml = make_musicxml([quarters(4)]).replace(
        "</score-partwise>", '<part id="P2"><measure number="1"/></part></score-partwise>'
    )

    [finding] = findings_for(xml, "unexpected-part-count")

    assert (finding.severity, finding.measure) == ("warning", None)
