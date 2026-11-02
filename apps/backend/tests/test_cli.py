from pathlib import Path

from backend import cli
from backend.errors import AudiverisNotFoundError, InvalidInputError, ValidationFailedError
from backend.transpose.pipeline import TransposeOutcome
from backend.transpose.register import ChosenInterval
from backend.validate.report import Finding, ValidationReport

ERROR_REPORT = ValidationReport([Finding("empty-measure", "error", "34", "no notes")])
WARNING_REPORT = ValidationReport([Finding("orphan-ending", "warning", "24", "no repeat")])


def test_validate_prints_findings_and_exits_one_on_error(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "validate_musicxml", lambda path: ERROR_REPORT)

    code = cli.main(["validate", str(tmp_path / "a.musicxml")])

    assert code == 1
    assert "bar 34: error empty-measure: no notes" in capsys.readouterr().out


def test_validate_strict_fails_on_warning_only(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "validate_musicxml", lambda path: WARNING_REPORT)
    target = str(tmp_path / "a.musicxml")

    assert cli.main(["validate", target]) == 0
    assert cli.main(["validate", target, "--strict"]) == 1


def test_validate_clean_file_exits_zero(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "validate_musicxml", lambda path: ValidationReport([]))

    assert cli.main(["validate", str(tmp_path / "a.musicxml")]) == 0
    assert capsys.readouterr().out == ""


def test_convert_prints_validation_findings_to_stderr_but_exits_zero(monkeypatch, tmp_path, capsys):
    result_path = tmp_path / "a.musicxml"
    monkeypatch.setattr(cli, "convert_pdf", lambda pdf, out, audiveris=None: [result_path])
    monkeypatch.setattr(cli, "validate_musicxml", lambda path: WARNING_REPORT)

    code = cli.main(["convert", str(tmp_path / "a.pdf")])

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == str(result_path)
    assert "a.musicxml" in captured.err and "bar 24: warning orphan-ending" in captured.err


def test_convert_reports_validation_failure_without_failing(monkeypatch, tmp_path, capsys):
    def unreadable(path):
        raise InvalidInputError("cannot read")

    monkeypatch.setattr(cli, "convert_pdf", lambda pdf, out, audiveris=None: [tmp_path / "a.musicxml"])
    monkeypatch.setattr(cli, "validate_musicxml", unreadable)

    code = cli.main(["convert", str(tmp_path / "a.pdf")])

    assert code == 0
    assert "cannot read" in capsys.readouterr().err


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


def outcome(path: Path, warnings: list[str] | None = None) -> TransposeOutcome:
    return TransposeOutcome(path, ChosenInterval("P4", "same", 0), ValidationReport([]), warnings or [])


def test_transpose_prints_path_and_reports_interval_on_stderr(monkeypatch, tmp_path, capsys):
    result = tmp_path / "out.musicxml"
    monkeypatch.setattr(cli, "transpose_musicxml", lambda *args: outcome(result, ["something odd"]))

    code = cli.main(["transpose", str(tmp_path / "a.musicxml"), "--from", "alto", "--out", str(result)])

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == str(result)
    assert "P4" in captured.err and "something odd" in captured.err


def test_transpose_default_output_name_uses_target_kind(monkeypatch, tmp_path):
    seen = []
    monkeypatch.setattr(cli, "transpose_musicxml", lambda source, out, *rest: seen.append(out) or outcome(out))

    cli.main(["transpose", str(tmp_path / "song.musicxml"), "--from", "alto"])
    cli.main(["transpose", str(tmp_path / "song.musicxml"), "--from", "tenor"])

    assert seen == [tmp_path / "song.tenor.musicxml", tmp_path / "song.alto.musicxml"]


def test_transpose_validation_failure_lists_findings_and_exits_one(monkeypatch, tmp_path, capsys):
    def refusing(*args):
        raise ValidationFailedError(ERROR_REPORT)

    monkeypatch.setattr(cli, "transpose_musicxml", refusing)

    code = cli.main(["transpose", str(tmp_path / "a.musicxml"), "--from", "alto"])

    captured = capsys.readouterr()
    assert code == 1
    assert "empty-measure" in captured.err
    assert captured.out == ""


def test_transpose_passes_register_and_force_flags(monkeypatch, tmp_path):
    seen = {}

    def recording(source, out, kind, register, force):
        seen.update(kind=kind, register=register, force=force)
        return outcome(out)

    monkeypatch.setattr(cli, "transpose_musicxml", recording)

    cli.main(["transpose", str(tmp_path / "a.musicxml"), "--from", "tenor", "--register", "shifted", "--force"])

    assert seen == {"kind": "tenor", "register": "shifted", "force": True}
