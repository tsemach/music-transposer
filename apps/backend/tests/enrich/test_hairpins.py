from layout_helpers import page, wedge

from backend.enrich.hairpins import PdfHairpin, find_hairpins
from backend.enrich.pdf_layout import Stroke


def test_wedge_opening_to_the_right_is_a_crescendo():
    found = find_hairpins(page(strokes=wedge(86.0, 303.0, 290.5, opens_right=True)))

    assert found == [PdfHairpin("crescendo", 86.0, 303.0, 290.5)]


def test_wedge_opening_to_the_left_is_a_diminuendo():
    found = find_hairpins(page(strokes=wedge(326.0, 548.0, 290.5, opens_right=False)))

    assert found == [PdfHairpin("diminuendo", 326.0, 548.0, 290.5)]


def test_two_hairpins_come_back_in_reading_order():
    strokes = wedge(326.0, 548.0, 290.5, False) + wedge(86.0, 303.0, 290.5, True)

    assert [h.kind for h in find_hairpins(page(strokes=strokes))] == ["crescendo", "diminuendo"]


def test_lone_slanted_stroke_is_ignored():
    assert find_hairpins(page(strokes=[Stroke(0.0, 0.0, 100.0, 3.0)])) == []


def test_steep_strokes_such_as_stems_or_ties_are_ignored():
    assert find_hairpins(page(strokes=wedge(10.0, 40.0, 100.0, True, rise=25.0))) == []


def test_short_wedges_are_ignored():
    assert find_hairpins(page(strokes=wedge(10.0, 18.0, 100.0, True, rise=1.5))) == []
