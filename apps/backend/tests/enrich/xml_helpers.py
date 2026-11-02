from xml.etree import ElementTree

HEAD = (
    '<score-partwise version="4.0"><part-list>'
    '<score-part id="P1"><part-name>Test</part-name></score-part></part-list>'
)


def note(default_x: int | None = 20, chord: bool = False) -> str:
    x = f' default-x="{default_x}"' if default_x is not None else ""
    chord_tag = "<chord/>" if chord else ""
    return f"<note{x}>{chord_tag}<pitch><step>C</step><octave>5</octave></pitch><duration>1</duration></note>"


def measure(number: int, width: int, notes: list[str], new_system: bool = False) -> str:
    layout = '<print new-system="yes"/>' if new_system else ""
    return f'<measure number="{number}" width="{width}">{layout}{"".join(notes)}</measure>'


def score(measures: list[str], extra_parts: int = 0) -> ElementTree.Element:
    parts = f'<part id="P1">{"".join(measures)}</part>'
    parts += "".join(f'<part id="P{n}">{measures[0]}</part>' for n in range(2, 2 + extra_parts))
    return ElementTree.fromstring(f"{HEAD}{parts}</score-partwise>")


def summary(measure_element: ElementTree.Element) -> list[str]:
    entries = []
    for child in measure_element:
        wedge = child.find(".//wedge")
        entries.append(f"wedge:{wedge.get('type')}" if wedge is not None else child.tag)
    return entries
