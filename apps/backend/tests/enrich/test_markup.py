from layout_helpers import FIRST_STAFF, page, wedge
from xml_helpers import measure, note, score, summary

from backend.enrich.markup import add_hairpins, add_tempo
from backend.enrich.pdf_layout import Staff
from backend.enrich.tempo import TempoMark

SECOND_STAFF = Staff(y_top=300.0, y_bottom=319.2, x_left=50.0, x_right=550.0)
FIRST = Staff(y_top=100.0, y_bottom=119.2, x_left=50.0, x_right=550.0)
THREE_NOTES = [note(20), note(100), note(180)]


def two_systems():
    return score(
        [
            measure(1, 250, THREE_NOTES),
            measure(2, 250, THREE_NOTES),
            measure(3, 250, THREE_NOTES, new_system=True),
            measure(4, 250, THREE_NOTES),
        ]
    )


def layout(*strokes_lists, staves=(FIRST, SECOND_STAFF)):
    return page(staves=list(staves), strokes=[s for strokes in strokes_lists for s in strokes])


def measures_of(root):
    return root.find("part").findall("measure")


def test_tempo_is_inserted_before_the_first_note_with_words_metronome_and_sound():
    root = two_systems()

    assert add_tempo(root, TempoMark("With attitude!", True, "quarter", 105)) is True

    first = measures_of(root)[0]
    assert [child.tag for child in first] == ["direction", "note", "note", "note"]
    words = first.find(".//words")
    assert words.text == "With attitude!" and words.get("font-weight") == "bold"
    assert first.find(".//beat-unit").text == "quarter"
    assert first.find(".//per-minute").text == "105"
    assert first.find("direction/sound").get("tempo") == "105"


def test_tempo_without_words_adds_no_words_element():
    root = two_systems()

    add_tempo(root, TempoMark("", False, "eighth", 160))

    first = measures_of(root)[0]
    assert first.find(".//words") is None
    assert first.find("direction/sound").get("tempo") == "80"


def test_existing_metronome_is_left_alone():
    root = two_systems()
    add_tempo(root, TempoMark("Swing", False, "quarter", 100))

    assert add_tempo(root, TempoMark("With attitude!", True, "quarter", 105)) is False
    assert len(root.findall(".//metronome")) == 1


def test_crescendo_starts_before_its_first_note_and_stops_at_measure_end():
    root = two_systems()
    pages = [layout(wedge(148.0, 305.0, 330.0, opens_right=True))]

    assert add_hairpins(root, pages) == []

    third = measures_of(root)[2]
    assert summary(third) == ["print", "note", "wedge:crescendo", "note", "note", "wedge:stop"]


def test_diminuendo_stops_before_the_first_note_after_its_end():
    root = two_systems()
    pages = [layout(wedge(320.0, 420.0, 330.0, opens_right=False))]

    add_hairpins(root, pages)

    fourth = measures_of(root)[3]
    assert summary(fourth) == ["wedge:diminuendo", "note", "note", "wedge:stop", "note"]


def test_hairpin_spanning_two_measures_stops_in_the_second():
    root = two_systems()
    pages = [layout(wedge(55.0, 450.0, 130.0, opens_right=True))]

    add_hairpins(root, pages)

    first, second = measures_of(root)[:2]
    assert summary(first) == ["wedge:crescendo", "note", "note", "note"]
    assert summary(second) == ["note", "note", "wedge:stop", "note"]


def test_placement_follows_the_side_of_the_staff():
    root = two_systems()
    below = layout(wedge(148.0, 305.0, 340.0, opens_right=True))
    add_hairpins(root, [below])
    assert measures_of(root)[2].find("direction").get("placement") == "below"

    root = two_systems()
    above = layout(wedge(148.0, 305.0, 290.0, opens_right=True))
    add_hairpins(root, [above])
    assert measures_of(root)[2].find("direction").get("placement") == "above"


def test_system_count_mismatch_skips_hairpins_with_a_warning():
    root = two_systems()
    pages = [layout(wedge(148.0, 305.0, 330.0, True), staves=(FIRST,))]

    warnings = add_hairpins(root, pages)

    assert root.findall(".//wedge") == []
    assert len(warnings) == 1 and "hairpin" in warnings[0].lower()


def test_multiple_parts_skip_hairpins_with_a_warning():
    root = score([measure(1, 250, THREE_NOTES), measure(2, 250, THREE_NOTES)], extra_parts=1)
    pages = [layout(wedge(60.0, 200.0, 130.0, True), staves=(FIRST,))]

    warnings = add_hairpins(root, pages)

    assert root.findall(".//wedge") == []
    assert len(warnings) == 1


def test_notes_without_positions_skip_hairpins_with_a_warning():
    root = score([measure(1, 500, [note(None), note(None)])])
    pages = [layout(wedge(60.0, 200.0, 130.0, True), staves=(FIRST,))]

    assert len(add_hairpins(root, pages)) == 1
    assert root.findall(".//wedge") == []


def test_page_without_hairpins_changes_nothing():
    root = two_systems()

    assert add_hairpins(root, [layout()]) == []
    assert root.findall(".//wedge") == []


def test_hairpin_starting_a_little_right_of_a_notehead_still_starts_on_that_note():
    root = score([measure(1, 500, [note(20), note(40), note(200)])])
    pages = [layout(wedge(75.0, 400.0, 130.0, opens_right=True), staves=(FIRST,))]

    add_hairpins(root, pages)

    assert summary(measures_of(root)[0])[:3] == ["wedge:crescendo", "note", "note"]


def test_hairpin_starting_near_the_barline_starts_on_the_next_measures_first_note():
    root = two_systems()
    pages = [layout(wedge(296.0, 420.0, 130.0, opens_right=True), staves=(FIRST, SECOND_STAFF))]

    add_hairpins(root, pages)

    assert summary(measures_of(root)[0]) == ["note", "note", "note"]
    assert summary(measures_of(root)[1])[0] == "wedge:crescendo"
