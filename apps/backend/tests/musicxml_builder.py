HEADER = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<score-partwise version="4.0"><part-list>'
    '<score-part id="P1"><part-name>Test</part-name></score-part></part-list>'
)


def make_musicxml(
    measures: list[str],
    beats: int = 4,
    beat_type: int = 4,
    first_attributes: str = "",
    measure_numbers: list[str] | None = None,
    include_time: bool = True,
) -> str:
    numbers = measure_numbers or [str(index) for index in range(1, len(measures) + 1)]
    time = f"<time><beats>{beats}</beats><beat-type>{beat_type}</beat-type></time>" if include_time else ""
    rendered = []
    for index, (number, content) in enumerate(zip(numbers, measures)):
        attributes = (
            f"<attributes><divisions>1</divisions>{first_attributes}{time}</attributes>"
            if index == 0
            else ""
        )
        rendered.append(f'<measure number="{number}">{attributes}{content}</measure>')
    return f'{HEADER}<part id="P1">{"".join(rendered)}</part></score-partwise>'


def quarters(count: int) -> str:
    note = "<note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>"
    return note * count


def whole_rest() -> str:
    return '<note><rest measure="yes"/><duration>4</duration></note>'
