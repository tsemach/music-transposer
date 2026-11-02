import zipfile
from pathlib import Path

import pytest

from backend.errors import InvalidInputError
from backend.mxl import extract_musicxml

CONTAINER = """<?xml version="1.0" encoding="UTF-8"?>
<container><rootfiles><rootfile full-path="{root}"/></rootfiles></container>"""


def make_mxl(path: Path, root: str = "score.xml", body: str = "<score-partwise/>") -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("META-INF/container.xml", CONTAINER.format(root=root))
        archive.writestr(root, body)
    return path


def test_extracts_rootfile_named_in_container(tmp_path):
    mxl = make_mxl(tmp_path / "piece.mxl", root="inner/main.xml", body="<score-partwise>x</score-partwise>")

    result = extract_musicxml(mxl, tmp_path / "out")

    assert result.read_text(encoding="utf-8") == "<score-partwise>x</score-partwise>"


def test_output_named_after_mxl_stem_with_hebrew_name(tmp_path):
    mxl = make_mxl(tmp_path / "שיר.mxl")

    result = extract_musicxml(mxl, tmp_path / "out")

    assert result == tmp_path / "out" / "שיר.musicxml"


def test_not_a_zip_raises_invalid_input(tmp_path):
    broken = tmp_path / "broken.mxl"
    broken.write_text("not a zip")

    with pytest.raises(InvalidInputError):
        extract_musicxml(broken, tmp_path / "out")


def test_missing_container_raises_invalid_input(tmp_path):
    mxl = tmp_path / "nocontainer.mxl"
    with zipfile.ZipFile(mxl, "w") as archive:
        archive.writestr("score.xml", "<score-partwise/>")

    with pytest.raises(InvalidInputError):
        extract_musicxml(mxl, tmp_path / "out")
