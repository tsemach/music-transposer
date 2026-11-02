from music21 import chord, key, meter, note, stream

BEATS_PER_MEASURE = 4


def make_score(pitches: list[str], key_fifths: int | None = None) -> stream.Score:
    part = stream.Part()
    measure = stream.Measure(number=1)
    measure.append(meter.TimeSignature("4/4"))
    if key_fifths is not None:
        measure.insert(0, key.KeySignature(key_fifths))
    for index, spec in enumerate(pitches):
        if index and index % BEATS_PER_MEASURE == 0:
            part.append(measure)
            measure = stream.Measure(number=index // BEATS_PER_MEASURE + 1)
        measure.append(_element(spec))
    part.append(measure)
    score = stream.Score()
    score.insert(0, part)
    return score


def _element(spec: str) -> note.GeneralNote:
    names = spec.split()
    if len(names) == 1:
        return note.Note(names[0], quarterLength=1)
    return chord.Chord(names, quarterLength=1)
