from backend.validate.report import Finding, ValidationReport

ERROR = Finding("empty-measure", "error", "34", "no notes")
WARNING = Finding("orphan-ending", "warning", "24", "ending without repeat")


def test_has_errors_true_only_with_error_findings():
    assert ValidationReport([ERROR, WARNING]).has_errors
    assert not ValidationReport([WARNING]).has_errors
    assert not ValidationReport([]).has_errors


def test_passes_ignores_warnings_unless_strict():
    report = ValidationReport([WARNING])

    assert report.passes()
    assert not report.passes(strict=True)
    assert not ValidationReport([ERROR]).passes()


def test_format_lines_with_and_without_measure():
    score_level = Finding("missing-time-signature", "error", None, "no time signature")

    lines = ValidationReport([ERROR, score_level]).format_lines()

    assert lines == [
        "bar 34: error empty-measure: no notes",
        "score: error missing-time-signature: no time signature",
    ]
