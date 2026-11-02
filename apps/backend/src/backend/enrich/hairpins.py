from dataclasses import dataclass
from itertools import combinations
from typing import Literal

from .pdf_layout import PageLayout, Stroke

MIN_LENGTH = 20.0
MIN_OPENING = 1.5
MAX_OPENING = 8.0
MAX_SLOPE = 0.25
JOIN_TOLERANCE = 0.6

HairpinKind = Literal["crescendo", "diminuendo"]


@dataclass(frozen=True)
class PdfHairpin:
    kind: HairpinKind
    x_start: float
    x_end: float
    y: float


def find_hairpins(page: PageLayout) -> list[PdfHairpin]:
    candidates = [stroke for stroke in page.strokes if _is_wedge_arm(stroke)]
    found = [hairpin for pair in combinations(candidates, 2) if (hairpin := _pair(*pair))]
    return sorted(found, key=lambda hairpin: (hairpin.y, hairpin.x_start))


def _is_wedge_arm(stroke: Stroke) -> bool:
    run = abs(stroke.x1 - stroke.x0)
    rise = abs(stroke.y1 - stroke.y0)
    return run >= MIN_LENGTH and MIN_OPENING <= rise <= MAX_OPENING and rise / run <= MAX_SLOPE


def _pair(first: Stroke, second: Stroke) -> PdfHairpin | None:
    for apex_first, far_first in _ends(first):
        for apex_second, far_second in _ends(second):
            if not _same_point(apex_first, apex_second):
                continue
            if abs(far_first[0] - far_second[0]) > JOIN_TOLERANCE:
                continue
            if (far_first[1] - apex_first[1]) * (far_second[1] - apex_second[1]) >= 0:
                continue
            kind: HairpinKind = "crescendo" if far_first[0] > apex_first[0] else "diminuendo"
            low, high = sorted((apex_first[0], far_first[0]))
            return PdfHairpin(kind, low, high, apex_first[1])
    return None


def _ends(stroke: Stroke) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    start, end = (stroke.x0, stroke.y0), (stroke.x1, stroke.y1)
    return [(start, end), (end, start)]


def _same_point(first: tuple[float, float], second: tuple[float, float]) -> bool:
    return abs(first[0] - second[0]) <= JOIN_TOLERANCE and abs(first[1] - second[1]) <= JOIN_TOLERANCE
