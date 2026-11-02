# Phase 2: Validate MusicXML Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Report which measures of an OMR-produced MusicXML look wrong, so a human knows where to look before converting further.

**Architecture:** A `backend.validate` subpackage with one module per concern: report types, structural checks on the raw XML (ElementTree), and a duration check via music21. `validate_musicxml(path)` combines them. The CLI gets a `validate` command, and `convert` prints the report to stderr after converting.

**Tech Stack:** Python 3, pytest, music21 (durations only), `xml.etree.ElementTree`.

**Spec:** `docs/superpowers/specs/2026-11-02-pdf-to-musicxml-design.md` (Phase 2). Evidence for the checks: `docs/superpowers/findings/2026-11-02-omr-spike.md`.

## Global Constraints

- Same as the Phase 0–1 plan: files under ~300 lines, no comments by default, tests follow 80/20, UTF-8 everywhere.
- Allow a short first measure (pickup) and a short final measure (spec Phase 2). A too-long measure anywhere is an error.
- OMR output stays the source of truth: validation reports, it never edits the file.
- Fixtures are crafted XML, not real sheet output (sample PDFs are third-party copyrighted and untracked).
- Measure labels are strings straight from the XML `number` attribute (may be `"0"`, `"X1"`).

## Review Focus

- Non-numeric or zero measure numbers (`"0"`, `"X1"`): labels preserved, no crash.
- Pickup measure and short final bar: not flagged. A too-long middle bar: flagged.
- A real multi-measure rest (`<multiple-rest>`) and a normal full-measure rest: not flagged as empty or wrong length.
- A real volta (ending with a backward repeat) and a genuine modulation that lasts longer than 8 measures: not flagged.
- Missing file or non-XML input: clear `InvalidInputError`, no traceback.

## File Structure

- `apps/backend/src/backend/validate/__init__.py` — `validate_musicxml`.
- `apps/backend/src/backend/validate/report.py` — `Finding`, `ValidationReport`.
- `apps/backend/src/backend/validate/structure.py` — XML checks.
- `apps/backend/src/backend/validate/durations.py` — music21 duration check.
- `apps/backend/src/backend/cli.py` — modify: `validate` command, report after `convert`.
- `apps/backend/tests/musicxml_builder.py` — fixture helper.
- `apps/backend/tests/validate/` — one test file per module, plus the integration test.

---

### Task 1: Report types and fixture builder

**Files:**
- Create: `validate/__init__.py` (empty for now), `validate/report.py`, `tests/musicxml_builder.py`, `tests/validate/test_report.py`

**Interfaces:**
- Produces in `report.py`:
  - `Severity = Literal["error", "warning"]`
  - `@dataclass(frozen=True) class Finding: check: str; severity: Severity; measure: str | None; message: str`
  - `@dataclass class ValidationReport: findings: list[Finding]` with `errors -> list[Finding]`, `warnings -> list[Finding]`, `has_errors -> bool`, `passes(strict: bool = False) -> bool` (strict also fails on warnings), `format_lines() -> list[str]`: `"bar 34: error empty-measure: <message>"`, or `"score: warning <check>: <message>"` when `measure is None`.
- Produces in `musicxml_builder.py`: `make_musicxml(measures: list[str], beats: int = 4, beat_type: int = 4, first_attributes: str = "") -> str`. Each string is the inner XML of one `<measure>`; numbers default to 1..n. The first measure gets `<attributes><divisions>1</divisions><time>…</time>{first_attributes}</attributes>`. Also `quarters(n: int) -> str` (n quarter notes, C4) and `whole_rest() -> str` (one full 4/4 rest, `<rest measure="yes"/>`). Add `measure_numbers: list[str] | None = None` to override numbers.

- [ ] **Step 1: Write failing tests** `test_passes_ignores_warnings_unless_strict`, `test_has_errors_true_only_with_error_findings`, `test_format_lines_with_and_without_measure`.
- [ ] **Step 2: Run** `apps/backend/.venv/bin/pytest apps/backend/tests/validate/test_report.py -v`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement `report.py`** and the builder.
- [ ] **Step 4: Run again.** Expected: PASS.
- [ ] **Step 5: Commit.**

---

### Task 2: Basic structure checks

**Files:**
- Create: `validate/structure.py`, `tests/validate/test_structure_basic.py`

**Interfaces:**
- Consumes: `Finding` (Task 1), `make_musicxml`, `quarters`, `whole_rest`.
- Produces: `check_structure(root: Element) -> list[Finding]`. This task adds:
  - `empty-measure` (error): a measure with no `<note>` elements and no `<multiple-rest>` in its `measure-style`. Message names the bar.
  - `missing-time-signature` (error, `measure=None`): no `<time>` anywhere in the part.
  - `unexpected-part-count` (warning, `measure=None`): not exactly one `<part>`.

- [ ] **Step 1: Write failing tests** with fixtures: `test_empty_measure_flagged_with_its_label`, `test_full_measure_rest_is_not_empty`, `test_multiple_rest_measure_is_not_empty` (first measure carries `<measure-style><multiple-rest>4</multiple-rest></measure-style>` and no notes), `test_non_numeric_measure_label_preserved` (labels `"0"`, `"X1"`), `test_missing_time_signature_flagged`, `test_two_parts_gives_warning`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement `check_structure`** iterating the first part's `<measure>` elements.
- [ ] **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: Commit.**

---

### Task 3: Key-signature flip and orphan endings

**Files:**
- Modify: `validate/structure.py`
- Create: `tests/validate/test_structure_suspicious.py`

**Interfaces:**
- Consumes: Task 2's `check_structure`. Add `MAX_KEY_FLIP_SPAN = 8` to `structure.py`.
- Produces two more checks in `check_structure`:
  - `key-signature-flip` (warning): the key `fifths` changes at bar *i* and returns to the previous value at bar *j* with `j - i ≤ MAX_KEY_FLIP_SPAN` (counted in measures). Finding is on bar *i*; message names both bars and both key values. The key before any `<key>` element counts as 0. Evidence: Gymnopédie bar 66 (−1) returns to 0 at bar 72.
  - `orphan-ending` (warning): an `<ending type="start">` while the part contains no `<repeat direction="backward">` at all. One finding per ending start. Evidence: Gymnopédie bars 24, 31, 40, 72.

- [ ] **Step 1: Write failing tests:** `test_key_change_that_returns_within_span_is_flagged_on_first_bar`, `test_modulation_longer_than_span_not_flagged`, `test_key_set_in_first_measure_is_not_a_change`, `test_ending_without_any_repeat_is_flagged`, `test_ending_with_backward_repeat_not_flagged`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement both checks** in `structure.py`; if the file passes ~250 lines, move each check into its own function and keep `check_structure` as the thin combiner.
- [ ] **Step 4: Run the whole `tests/validate` directory.** Expected: PASS.
- [ ] **Step 5: Commit.**

---

### Task 4: Duration check

**Files:**
- Create: `validate/durations.py`, `tests/validate/test_durations.py`

**Interfaces:**
- Consumes: `Finding`, `InvalidInputError`.
- Produces: `check_durations(path: Path) -> list[Finding]`. Parses with `music21.converter.parse`; for each measure of the first part, compares `highestTime` to the governing time signature's `barDuration.quarterLength`. `measure-duration` (error) when the measure is longer, or shorter and neither the first nor the last measure. Message gives found vs expected quarter lengths. Label is `str(measure.number)`.

- [ ] **Step 1: Write failing tests** (builder fixtures written to `tmp_path`): `test_long_middle_measure_flagged`, `test_short_middle_measure_flagged`, `test_short_first_measure_pickup_not_flagged`, `test_short_last_measure_not_flagged`, `test_multiple_rest_and_full_rest_measures_not_flagged`, `test_all_correct_gives_no_findings`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement `check_durations`.**
- [ ] **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: Commit.**

---

### Task 5: `validate_musicxml`, CLI and real-sheet regression

**Files:**
- Modify: `validate/__init__.py`, `cli.py`, `tests/test_cli.py`
- Create: `tests/validate/test_validate.py`, `tests/validate/test_integration_sheets_validation.py`

**Interfaces:**
- Consumes: `check_structure`, `check_durations`, `ValidationReport`, `InvalidInputError`.
- Produces:
  - `validate_musicxml(path: Path) -> ValidationReport` — structure findings then duration findings. Raises `InvalidInputError` for a missing file or XML that doesn't parse.
  - CLI `validate <musicxml> [--strict]`: prints `format_lines()` on stdout, exit 0 if `report.passes(strict)`, else 1; `BackendError` → stderr, exit 1.
  - `convert` additionally prints each output's findings to stderr, prefixed with the file name; exit code is unchanged by findings.

- [ ] **Step 1: Write failing tests:** `test_validate_missing_file_raises_invalid_input`, `test_validate_non_xml_raises_invalid_input`, `test_validate_combines_structure_and_duration_findings`; in `test_cli.py`: `test_validate_prints_findings_and_exits_one_on_error`, `test_validate_strict_fails_on_warning_only`, `test_validate_clean_file_exits_zero`, `test_convert_prints_validation_findings_to_stderr_but_exits_zero` (monkeypatch `cli.validate_musicxml`).
- [ ] **Step 2: Write the integration test** `test_known_problems_on_sample_sheets`, skipped without Audiveris or sheets: converts each sample with `convert_pdf` and asserts, pinned to Audiveris 5.11.0 output: Amazing Grace has an `empty-measure` error on bar `"34"`; Gymnopédie has a `key-signature-flip` warning on `"66"` and `orphan-ending` warnings including `"24"`; Funk Out has no errors.
- [ ] **Step 3: Run the unit tests.** Expected: FAIL.
- [ ] **Step 4: Implement** `validate_musicxml` and the CLI changes.
- [ ] **Step 5: Run the full suite.** Expected: all pass, integration included.
- [ ] **Step 6: Run `apps/backend/.venv/bin/python -m backend convert sheets/gymnopedie-no-1-alto-saxophone.pdf --out <scratch>`.** Expected: stderr lists the key flip at bar 66 and the orphan endings; stdout lists the `.musicxml` path; exit 0.
- [ ] **Step 7: Commit.**

---

## Self-review

- **Spec coverage:** Phase 2 asks for duration vs time signature (Task 4), pickup/final allowance (Task 4), part and time-signature present (Task 2), report listing flagged measures with reasons (Task 1, 5), non-zero exit (Task 5), crafted fixtures (Task 1), and "matches what a human sees" on the reference sheets (Task 5 integration). The spec's "key signature present" is intentionally dropped: Audiveris omits `<key>` for C major (Funk Out), so a missing key is not an error.
- **Known limit:** a multi-measure rest dropped entirely (Amazing Grace's opening 3 bars) leaves no trace in the MusicXML. Validation cannot detect it; only comparing against the PDF could.
- **Type consistency:** `Finding.measure` is `str | None` throughout; both check modules return `list[Finding]`; `validate_musicxml` returns `ValidationReport`.
- **Review Focus:** each of the five lines has a named test (Tasks 2–5).
- **My calls:** `key-signature-flip` and `orphan-ending` are warnings (heuristics), the hard structural problems are errors; `MAX_KEY_FLIP_SPAN = 8`; whether Phase 3 blocks on warnings is decided there.
