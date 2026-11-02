from layout_helpers import page, text_line

from backend.enrich.tempo import TempoMark, find_tempo

ATTITUDE = text_line(
    ("With attitude!", "TimesNewRomanPS-BoldMT"),
    (" ", "TimesNewRomanPSMT"),
    ("q", "OpusTextStd"),
    (" = 105", "TimesNewRomanPSMT"),
)


def test_finds_words_beat_unit_and_bpm_above_first_staff():
    assert find_tempo(page([ATTITUDE])) == TempoMark("With attitude!", True, "quarter", 105)


def test_tempo_without_words_has_empty_words():
    line = text_line(("q", "OpusTextStd"), (" = 90", "TimesNewRomanPSMT"))

    assert find_tempo(page([line])) == TempoMark("", False, "quarter", 90)


def test_eighth_and_half_units_are_recognised():
    eighth = text_line(("e", "OpusTextStd"), (" = 160", "Times"))
    half = text_line(("h", "OpusTextStd"), (" = 60", "Times"))

    assert find_tempo(page([eighth])).beat_unit == "eighth"
    assert find_tempo(page([half])).beat_unit == "half"


def test_equation_below_the_first_staff_is_not_a_tempo():
    line = text_line(("q", "OpusTextStd"), (" = 105", "Times"), y_top=300.0, y_bottom=312.0)

    assert find_tempo(page([line])) is None


def test_ordinary_text_is_not_a_tempo():
    assert find_tempo(page([text_line(("Alto Saxophone", "Times"))])) is None


def test_page_without_staves_has_no_tempo():
    assert find_tempo(page([ATTITUDE], staves=[])) is None
