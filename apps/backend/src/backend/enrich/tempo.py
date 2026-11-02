import re
from dataclasses import dataclass

from .pdf_layout import PageLayout, TextLine

BEAT_UNITS = {"q": "quarter", "♩": "quarter", "e": "eighth", "♪": "eighth", "h": "half"}
TEMPO_PATTERN = re.compile(r"(?:^|\s)(?P<unit>[qeh♩♪])\s*=\s*(?P<bpm>\d{2,3})\s*$")
STAFF_TOP_TOLERANCE = 2.0
BOLD_MARKERS = ("bold", "black", "heavy")


@dataclass(frozen=True)
class TempoMark:
    words: str
    bold: bool
    beat_unit: str
    bpm: int


def find_tempo(page: PageLayout) -> TempoMark | None:
    if not page.staves:
        return None
    first_staff_top = min(staff.y_top for staff in page.staves)
    for line in page.lines:
        if line.y_bottom > first_staff_top + STAFF_TOP_TOLERANCE:
            continue
        mark = _parse(line)
        if mark:
            return mark
    return None


def _parse(line: TextLine) -> TempoMark | None:
    text = "".join(span.text for span in line.spans).strip()
    match = TEMPO_PATTERN.search(text)
    if not match:
        return None
    words = text[: match.start()].strip()
    return TempoMark(words, _is_bold(line, words), BEAT_UNITS[match.group("unit")], int(match.group("bpm")))


def _is_bold(line: TextLine, words: str) -> bool:
    if not words:
        return False
    wording = [span for span in line.spans if span.text.strip() and span.text.strip() in words]
    return bool(wording) and all(any(m in span.font.lower() for m in BOLD_MARKERS) for span in wording)
