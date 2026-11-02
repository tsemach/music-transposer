from backend.enrich.pdf_layout import PageLayout, Staff, Stroke, TextLine, TextSpan

FIRST_STAFF = Staff(y_top=197.0, y_bottom=216.2, x_left=53.0, x_right=553.0)


def text_line(*spans: tuple[str, str], y_top: float = 172.0, y_bottom: float = 184.0) -> TextLine:
    return TextLine(tuple(TextSpan(text, font) for text, font in spans), y_top, y_bottom)


def page(
    lines: list[TextLine] | None = None,
    staves: list[Staff] | None = None,
    strokes: list[Stroke] | None = None,
) -> PageLayout:
    return PageLayout(lines or [], staves if staves is not None else [FIRST_STAFF], strokes or [])


def wedge(x_start: float, x_end: float, y: float, opens_right: bool, rise: float = 3.0) -> list[Stroke]:
    apex_x, open_x = (x_start, x_end) if opens_right else (x_end, x_start)
    return [Stroke(apex_x, y, open_x, y - rise), Stroke(apex_x, y, open_x, y + rise)]
