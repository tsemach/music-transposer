import zipfile
from pathlib import Path

from backend import convert
from backend.convert import convert_pdf


def write_mxl(path: Path) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "META-INF/container.xml",
            '<container><rootfiles><rootfile full-path="s.xml"/></rootfiles></container>',
        )
        archive.writestr("s.xml", "<score-partwise/>")
    return path


def test_convert_returns_musicxml_for_each_mxl(monkeypatch, tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    produced = [write_mxl(out_dir / "a.mvt2.mxl"), write_mxl(out_dir / "a.mxl")]
    monkeypatch.setattr(convert, "run_omr", lambda pdf, out, exe, **_: produced)
    monkeypatch.setattr(convert, "find_audiveris", lambda override=None: Path("/fake/Audiveris"))

    result = convert_pdf(tmp_path / "a.pdf", out_dir)

    assert [p.name for p in result] == ["a.mvt2.musicxml", "a.musicxml"]
    assert all(p.is_file() for p in result)


def test_convert_uses_override_path(monkeypatch, tmp_path):
    seen = {}

    def fake_find(override=None):
        seen["override"] = override
        return override

    monkeypatch.setattr(convert, "find_audiveris", fake_find)
    monkeypatch.setattr(convert, "run_omr", lambda pdf, out, exe, **_: [])
    override = tmp_path / "custom" / "Audiveris"

    convert_pdf(tmp_path / "a.pdf", tmp_path / "out", override)

    assert seen["override"] == override
