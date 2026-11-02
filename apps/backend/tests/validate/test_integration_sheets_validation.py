from pathlib import Path

import pytest

from backend.audiveris_locator import find_audiveris
from backend.convert import convert_pdf
from backend.errors import AudiverisNotFoundError
from backend.validate import validate_musicxml

SHEETS_DIR = Path(__file__).resolve().parents[4] / "sheets"


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


def report_for(sheet: str, tmp_path):
    outputs = convert_pdf(SHEETS_DIR / sheet, tmp_path / "out")
    return validate_musicxml(outputs[0])


def pairs(report):
    return {(finding.check, finding.measure) for finding in report.findings}


def test_known_problems_on_sample_sheets(tmp_path):
    amazing_grace = report_for("amazing-grace-alto-sax.pdf", tmp_path / "ag")
    gymnopedie = report_for("gymnopedie-no-1-alto-saxophone.pdf", tmp_path / "gy")
    funk_out = report_for("funk-out-alto-saxophone.pdf", tmp_path / "fu")

    assert ("empty-measure", "34") in pairs(amazing_grace)
    assert ("key-signature-flip", "66") in pairs(gymnopedie)
    assert ("orphan-ending", "24") in pairs(gymnopedie)
    assert not funk_out.has_errors
