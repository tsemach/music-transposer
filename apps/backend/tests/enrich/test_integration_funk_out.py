from pathlib import Path
from xml.etree import ElementTree

import pytest

from backend.audiveris_locator import find_audiveris
from backend.errors import ExecutableNotFoundError
from backend.musescore_locator import find_musescore
from backend.pipeline import run_pipeline

SHEET = Path(__file__).resolve().parents[4] / "sheets" / "funk-out-alto-saxophone.pdf"


def tools_available() -> bool:
    try:
        find_audiveris()
        find_musescore()
    except ExecutableNotFoundError:
        return False
    return True


@pytest.mark.skipif(not (SHEET.is_file() and tools_available()), reason="needs Audiveris, MuseScore and the sample sheet")
def test_funk_out_keeps_its_tempo_and_hairpins(tmp_path):
    result = run_pipeline(SHEET, tmp_path / "out", "alto")

    tenor = ElementTree.parse(result.tenor_musicxml).getroot()
    assert tenor.find(".//words").text == "With attitude!"
    assert tenor.find(".//per-minute").text == "105"
    wedge_types = [wedge.get("type") for wedge in tenor.iter("wedge")]
    assert [kind for kind in wedge_types if kind != "stop"] == ["crescendo", "diminuendo", "crescendo"]
    assert wedge_types.count("stop") == 3
    assert result.warnings == []
