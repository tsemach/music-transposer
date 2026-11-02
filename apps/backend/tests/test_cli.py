from pathlib import Path

from backend import cli
from backend.errors import AudiverisNotFoundError


def test_cli_prints_paths_and_returns_zero(monkeypatch, tmp_path, capsys):
    result_path = tmp_path / "out" / "a.musicxml"
    monkeypatch.setattr(cli, "convert_pdf", lambda pdf, out, audiveris=None: [result_path])

    code = cli.main(["convert", str(tmp_path / "a.pdf"), "--out", str(tmp_path / "out")])

    assert code == 0
    assert capsys.readouterr().out.strip() == str(result_path)


def test_cli_returns_one_and_prints_error_on_backend_error(monkeypatch, tmp_path, capsys):
    def failing(pdf, out, audiveris=None):
        raise AudiverisNotFoundError("Audiveris not found")

    monkeypatch.setattr(cli, "convert_pdf", failing)

    code = cli.main(["convert", str(tmp_path / "a.pdf")])

    captured = capsys.readouterr()
    assert code == 1
    assert "Audiveris not found" in captured.err
    assert captured.out == ""


def test_cli_default_out_dir_is_beside_pdf(monkeypatch, tmp_path):
    seen = {}

    def recording(pdf, out, audiveris=None):
        seen["out"] = out
        return []

    monkeypatch.setattr(cli, "convert_pdf", recording)

    cli.main(["convert", str(tmp_path / "song.pdf")])

    assert seen["out"] == tmp_path / "song"


def test_cli_passes_audiveris_override(monkeypatch, tmp_path):
    seen = {}

    def recording(pdf, out, audiveris=None):
        seen["audiveris"] = audiveris
        return []

    monkeypatch.setattr(cli, "convert_pdf", recording)

    cli.main(["convert", str(tmp_path / "a.pdf"), "--audiveris", "/x/Audiveris"])

    assert seen["audiveris"] == Path("/x/Audiveris")
