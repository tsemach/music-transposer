from xml.etree import ElementTree

from musicxml_builder import make_musicxml, quarters

from backend.validate.structure import MAX_KEY_FLIP_SPAN, check_structure


def findings_for(xml: str, check: str):
    root = ElementTree.fromstring(xml)
    return [finding for finding in check_structure(root) if finding.check == check]


def key(fifths: int) -> str:
    return f"<attributes><key><fifths>{fifths}</fifths></key></attributes>"


def ending_start(number: int) -> str:
    return f'<barline location="left"><ending number="{number}" type="start"/></barline>'


BACKWARD_REPEAT = '<barline location="right"><repeat direction="backward"/></barline>'


def test_key_change_that_returns_within_span_is_flagged_on_first_bar():
    measures = [quarters(4)] * 8
    measures[2] = key(-1) + quarters(4)
    measures[5] = key(0) + quarters(4)

    [finding] = findings_for(make_musicxml(measures), "key-signature-flip")

    assert (finding.severity, finding.measure) == ("warning", "3")
    assert "6" in finding.message


def test_modulation_longer_than_span_not_flagged():
    length = MAX_KEY_FLIP_SPAN + 4
    measures = [quarters(4)] * length
    measures[1] = key(-1) + quarters(4)
    measures[1 + MAX_KEY_FLIP_SPAN + 1] = key(0) + quarters(4)

    assert findings_for(make_musicxml(measures), "key-signature-flip") == []


def test_key_set_in_first_measure_is_not_a_change():
    xml = make_musicxml([quarters(4)] * 3, first_attributes="<key><fifths>-2</fifths></key>")

    assert findings_for(xml, "key-signature-flip") == []


def test_ending_without_any_repeat_is_flagged():
    measures = [quarters(4), ending_start(1) + quarters(4), quarters(4), ending_start(2) + quarters(4)]

    labels = [f.measure for f in findings_for(make_musicxml(measures), "orphan-ending")]

    assert labels == ["2", "4"]


def test_ending_with_backward_repeat_not_flagged():
    measures = [quarters(4), ending_start(1) + quarters(4) + BACKWARD_REPEAT, quarters(4)]

    assert findings_for(make_musicxml(measures), "orphan-ending") == []
