from xml.etree.ElementTree import Element, SubElement

from .hairpins import PdfHairpin, find_hairpins
from .pdf_layout import PageLayout, Staff
from .systems import XmlSystem, positioned_notes, split_into_systems
from .tempo import TempoMark

NOTE_TOLERANCE = 4.0
NOTEHEAD_HALF_WIDTH = 4.0
BARLINE_SNAP = 0.03
QUARTERS_PER_UNIT = {"quarter": 1.0, "eighth": 0.5, "half": 2.0}


def add_tempo(root: Element, mark: TempoMark) -> bool:
    if root.find(".//metronome") is not None:
        return False
    measures = _measures(root)
    first_note = measures[0].find("note") if measures else None
    if first_note is None:
        return False
    first_measure = measures[0]
    first_measure.insert(list(first_measure).index(first_note), _tempo_direction(mark))
    return True


def _tempo_direction(mark: TempoMark) -> Element:
    direction = Element("direction", placement="above")
    if mark.words:
        words = SubElement(SubElement(direction, "direction-type"), "words")
        words.text = mark.words
        if mark.bold:
            words.set("font-weight", "bold")
    metronome = SubElement(SubElement(direction, "direction-type"), "metronome")
    SubElement(metronome, "beat-unit").text = mark.beat_unit
    SubElement(metronome, "per-minute").text = str(mark.bpm)
    SubElement(direction, "sound", tempo=f"{mark.bpm * QUARTERS_PER_UNIT[mark.beat_unit]:g}")
    return direction


def add_hairpins(root: Element, pages: list[PageLayout]) -> list[str]:
    found = [(page, hairpin) for page in pages for hairpin in find_hairpins(page)]
    if not found:
        return []
    parts = root.findall("part")
    measures = _measures(root)
    xml_systems = split_into_systems(measures)
    staves = [(page, staff) for page in pages for staff in page.staves]
    problem = _unsupported_reason(root, len(parts), len(xml_systems), len(staves))
    if problem:
        return [f"Hairpins found in the PDF were not restored: {problem}"]
    systems = [XmlSystem(group, staff) for group, (_, staff) in zip(xml_systems, staves)]
    unplaced = 0
    for number, (page, hairpin) in enumerate(found, start=1):
        system_index = _nearest_staff(staves, page, hairpin)
        if not _place(systems[system_index], measures, hairpin, number):
            unplaced += 1
    return [f"{unplaced} hairpin(s) found in the PDF could not be placed"] if unplaced else []


def _measures(root: Element) -> list[Element]:
    part = root.find("part")
    return part.findall("measure") if part is not None else []


def _unsupported_reason(root: Element, part_count: int, system_count: int, staff_count: int) -> str | None:
    if part_count != 1 or any(int(el.text or 1) > 1 for el in root.iter("staves")):
        return "only single-staff, single-part music is supported"
    if system_count != staff_count:
        return f"the PDF has {staff_count} staves but the music has {system_count} systems"
    return None


def _nearest_staff(staves: list[tuple[PageLayout, Staff]], page: PageLayout, hairpin: PdfHairpin) -> int:
    def distance(staff: Staff) -> float:
        if staff.y_top <= hairpin.y <= staff.y_bottom:
            return 0.0
        return min(abs(hairpin.y - staff.y_top), abs(hairpin.y - staff.y_bottom))

    candidates = [(distance(staff), index) for index, (owner, staff) in enumerate(staves) if owner is page]
    return min(candidates)[1]


def _place(system: XmlSystem, measures: list[Element], hairpin: PdfHairpin, number: int) -> bool:
    start = _start_slot(system, hairpin.x_start)
    stop = _stop_slot(system, hairpin.x_end)
    if start is None or stop is None:
        return False
    start_measure, start_note = start
    stop_measure, stop_note = stop
    if _before(measures, stop_measure, stop_note, start_measure, start_note):
        return False
    placement = "below" if hairpin.y > system.staff.y_bottom else "above"
    _insert(start_measure, start_note, _wedge(hairpin.kind, placement, number))
    _insert(stop_measure, stop_note, _wedge("stop", placement, number))
    return True


def _start_slot(system: XmlSystem, x: float) -> tuple[Element, Element] | None:
    index = system.measure_index_at(x)
    candidates: list[tuple[float, Element, Element]] = []
    for offset in (0, 1):
        if index + offset >= len(system.measures):
            continue
        notes = positioned_notes(system, index + offset)
        if notes is None:
            return None
        candidates += [(note_x, system.measures[index + offset], note) for note_x, note in notes]
    if not candidates:
        return None
    _, measure, note = min(candidates, key=lambda item: abs(item[0] + NOTEHEAD_HALF_WIDTH - x))
    return measure, note


def _stop_slot(system: XmlSystem, x: float) -> tuple[Element, Element | None] | None:
    index = system.measure_index_at(x)
    width = system.measure_right(index) - system.measure_left(index)
    if index > 0 and x - system.measure_left(index) < BARLINE_SNAP * width:
        index, x = index - 1, system.measure_right(index - 1)
    notes = positioned_notes(system, index)
    if notes is None:
        return None
    for note_x, note in notes:
        if note_x > x + NOTE_TOLERANCE:
            return system.measures[index], note
    return system.measures[index], None


def _before(measures: list[Element], stop_measure: Element, stop_note: Element | None, start_measure: Element, start_note: Element) -> bool:
    stop_key = (measures.index(stop_measure), _position(stop_measure, stop_note))
    start_key = (measures.index(start_measure), _position(start_measure, start_note))
    return stop_key <= start_key


def _position(measure: Element, note: Element | None) -> int:
    return len(measure) if note is None else list(measure).index(note)


def _insert(measure: Element, before: Element | None, direction: Element) -> None:
    if before is None:
        measure.append(direction)
    else:
        measure.insert(list(measure).index(before), direction)


def _wedge(kind: str, placement: str, number: int) -> Element:
    direction = Element("direction", placement=placement)
    SubElement(SubElement(direction, "direction-type"), "wedge", type=kind, number=str(number))
    return direction
