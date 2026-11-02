from pathlib import Path

import pytest

from backend.audiveris_locator import find_audiveris
from backend.errors import ExecutableNotFoundError
from backend.musescore_locator import find_musescore
from backend.pipeline import run_pipeline

SHEET = Path(__file__).resolve().parents[3] / "sheets" / "gymnopedie-no-1-alto-saxophone.pdf"


def tools_available() -> bool:
    try:
        find_audiveris()
        find_musescore()
    except ExecutableNotFoundError:
        return False
    return True


@pytest.mark.skipif(not (SHEET.is_file() and tools_available()), reason="needs Audiveris, MuseScore and the sample sheet")
def test_full_pipeline_on_gymnopedie(tmp_path):
    result = run_pipeline(SHEET, tmp_path / "out", "alto")

    data = result.pdf.read_bytes()
    assert data.startswith(b"%PDF") and len(data) > 5_000
    assert result.interval.register == "same"
