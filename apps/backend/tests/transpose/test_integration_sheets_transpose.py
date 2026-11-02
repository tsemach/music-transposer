from pathlib import Path

import pytest
from music21 import converter

from backend.audiveris_locator import find_audiveris
from backend.convert import convert_pdf
from backend.errors import AudiverisNotFoundError
from backend.transpose.pipeline import transpose_musicxml

SHEETS_DIR = Path(__file__).resolve().parents[4] / "sheets"

EXPECTED_REGISTER = {
    "gymnopedie-no-1-alto-saxophone": "same",
    "funk-out-alto-saxophone": "same",
    "amazing-grace-alto-sax": "shifted",
}


def audiveris_available() -> bool:
    try:
        find_audiveris()
    except AudiverisNotFoundError:
        return False
    return True


pytestmark = pytest.mark.skipif(
    not (SHEETS_DIR.is_dir() and audiveris_available()),
    reason="needs Audiveris installed and sample PDFs in sheets/",
)


def pitch_names(path: Path) -> list[str]:
    score = converter.parse(str(path))
    return [p.nameWithOctave for element in score.recurse().notes for p in element.pitches]


@pytest.mark.parametrize("stem", EXPECTED_REGISTER)
def test_sample_sheets_choose_expected_register_and_round_trip(stem, tmp_path):
    original = convert_pdf(SHEETS_DIR / f"{stem}.pdf", tmp_path / "ocr")[0]

    tenor = transpose_musicxml(original, tmp_path / "tenor.musicxml", "alto", force=True)
    back = transpose_musicxml(
        tenor.out_path, tmp_path / "alto-again.musicxml", "tenor", register=tenor.interval.register, force=True
    )

    assert (tenor.interval.register, tenor.interval.out_of_range) == (EXPECTED_REGISTER[stem], 0)
    assert pitch_names(back.out_path) == pitch_names(original)
