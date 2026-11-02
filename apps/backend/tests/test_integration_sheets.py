from pathlib import Path

import pytest
from music21 import converter

from backend.audiveris_locator import find_audiveris
from backend.convert import convert_pdf
from backend.errors import AudiverisNotFoundError

SHEETS_DIR = Path(__file__).resolve().parents[3] / "sheets"
SHEETS = sorted(SHEETS_DIR.glob("*.pdf"))


def audiveris_available() -> bool:
    try:
        find_audiveris()
    except AudiverisNotFoundError:
        return False
    return True


pytestmark = pytest.mark.skipif(
    not (SHEETS and audiveris_available()),
    reason="needs Audiveris installed and sample PDFs in sheets/",
)


@pytest.mark.parametrize("pdf", SHEETS, ids=lambda p: p.stem)
def test_each_sample_pdf_converts_and_parses(pdf, tmp_path):
    outputs = convert_pdf(pdf, tmp_path / "out")

    assert outputs
    score = converter.parse(outputs[0])
    assert len(score.parts[0].getElementsByClass("Measure")) >= 1
