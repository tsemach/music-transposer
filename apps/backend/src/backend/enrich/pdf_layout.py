from dataclasses import dataclass
from pathlib import Path

import pymupdf

MIN_STAFF_LINE_LENGTH = 100.0
MAX_STAFF_LINE_GAP = 10.0
LINES_PER_STAFF = 5
FLAT_TOLERANCE = 0.01
THIN_RECT_HEIGHT = 1.5


@dataclass(frozen=True)
class TextSpan:
    text: str
    font: str


@dataclass(frozen=True)
class TextLine:
    spans: tuple[TextSpan, ...]
    y_top: float
    y_bottom: float


@dataclass(frozen=True)
class Staff:
    y_top: float
    y_bottom: float
    x_left: float
    x_right: float


@dataclass(frozen=True)
class Stroke:
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass
class PageLayout:
    lines: list[TextLine]
    staves: list[Staff]
    strokes: list[Stroke]


def read_pdf_layout(pdf: Path) -> list[PageLayout]:
    with pymupdf.open(pdf) as document:
        return [_read_page(page) for page in document]


def _read_page(page: pymupdf.Page) -> PageLayout:
    horizontals: list[tuple[float, float, float]] = []
    strokes: list[Stroke] = []
    for drawing in page.get_drawings():
        for item in drawing["items"]:
            _collect(item, horizontals, strokes)
    return PageLayout(_read_lines(page), _group_staves(horizontals), strokes)


def _collect(item: tuple, horizontals: list[tuple[float, float, float]], strokes: list[Stroke]) -> None:
    if item[0] == "l":
        start, end = item[1], item[2]
        if abs(start.y - end.y) < FLAT_TOLERANCE:
            horizontals.append((start.y, min(start.x, end.x), max(start.x, end.x)))
        else:
            strokes.append(Stroke(start.x, start.y, end.x, end.y))
    elif item[0] == "re" and item[1].height < THIN_RECT_HEIGHT:
        rect = item[1]
        horizontals.append(((rect.y0 + rect.y1) / 2, rect.x0, rect.x1))


def _read_lines(page: pymupdf.Page) -> list[TextLine]:
    lines = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = tuple(TextSpan(span["text"], span["font"]) for span in line["spans"])
            lines.append(TextLine(spans, line["bbox"][1], line["bbox"][3]))
    return lines


def _group_staves(horizontals: list[tuple[float, float, float]]) -> list[Staff]:
    long_lines = sorted(line for line in horizontals if line[2] - line[1] >= MIN_STAFF_LINE_LENGTH)
    groups: list[list[tuple[float, float, float]]] = []
    for line in long_lines:
        if groups and line[0] - groups[-1][-1][0] < MAX_STAFF_LINE_GAP:
            groups[-1].append(line)
        else:
            groups.append([line])
    return [
        Staff(group[0][0], group[-1][0], min(g[1] for g in group), max(g[2] for g in group))
        for group in groups
        if len(group) == LINES_PER_STAFF
    ]
