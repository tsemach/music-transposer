# Phase 0–1: OMR Spike and PDF → MusicXML CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decide whether Audiveris is good enough on the sample sheets, then ship a CLI that turns a PDF into MusicXML.

**Architecture:** A spike (Task 1) produces a written finding that gates the rest. The product is a small Python package in `apps/backend` with one module per responsibility: locate Audiveris, run it, unzip `.mxl`, orchestrate, CLI. The same `convert_pdf` function is reused later by the sidecar loop.

**Tech Stack:** Python 3, pytest, music21 (spike and integration test only), Audiveris (user-installed, subprocess), argparse.

**Spec:** `docs/superpowers/specs/2026-11-02-pdf-to-musicxml-design.md`

## Global Constraints

- Audiveris is user-installed, never bundled; path auto-detected and overridable (CLAUDE.md).
- Call shape: `audiveris -batch -export -output <dir> -- <file.pdf>` produces `.mxl` (CLAUDE.md; Task 1 confirms).
- Audiveris reads the PDF directly; no PyMuPDF image step in this phase (spec C1).
- Pass file paths, never contents. UTF-8 everywhere; Hebrew file names must work (CLAUDE.md).
- Files under ~300 lines, no comments by default, tests follow 80/20 (project rules).
- Benchmark set: `sheets/amazing-grace-alto-sax.pdf`, `sheets/funk-out-alto-saxophone.pdf`, `sheets/gymnopedie-no-1-alto-saxophone.pdf`.
- Do not run dev servers. Do not write docs beyond the Task 1 findings file.

## Review Focus

- PDF path containing spaces or Hebrew characters: must convert, not crash on encoding.
- Path that doesn't exist or isn't a PDF: clear error, no Audiveris launch.
- Audiveris exits 0 but writes no `.mxl`: explicit `NoOutputError`, not an empty success.
- Audiveris hangs: killed after the timeout with a clear error.
- Re-running into an output dir that already holds old results: must not return stale files from a previous run.

## File Structure

- `apps/backend/pyproject.toml` — package metadata, pytest config, deps.
- `apps/backend/package.json` — `test` script so Turbo can run it.
- `apps/backend/src/backend/errors.py` — exception types.
- `apps/backend/src/backend/audiveris_locator.py` — find the executable.
- `apps/backend/src/backend/omr.py` — run Audiveris, return `.mxl` paths.
- `apps/backend/src/backend/mxl.py` — `.mxl` → `.musicxml`.
- `apps/backend/src/backend/convert.py` — orchestration.
- `apps/backend/src/backend/cli.py`, `__main__.py` — `python -m backend convert`.
- `apps/backend/tests/` — one test file per module.
- `docs/superpowers/findings/2026-11-02-omr-spike.md` — Task 1 output.

---

### Task 1: OMR spike (throwaway, gates everything else)

**Files:**
- Create: `docs/superpowers/findings/2026-11-02-omr-spike.md`
- Scratch scripts go in the session scratchpad, not the repo.

**Interfaces:**
- Produces: the finding file. Task 5 reads from it: the exact Audiveris binary path, the real output file names and extensions, and whether multi-file output occurs. Task 3 reads the install location for the default search paths.

- [ ] **Step 1: Install Audiveris and MuseScore on the WSL2 dev machine.** Record versions, install method and the executable paths in the findings file.
- [ ] **Step 2: Create a venv at `apps/backend/.venv` and install music21.** Confirm `.venv` is gitignored; add it if not.
- [ ] **Step 3: Run `audiveris -batch -export -output <scratch>/<name> -- <pdf>` on each of the three sample PDFs.** Record exit code, wall time, and the exact files produced.
- [ ] **Step 4: For each result, load with `music21.converter.parse` and record** measure count, time/key signature, part name and instrument, and every measure whose total duration differs from the time signature.
- [ ] **Step 5: Open each result in MuseScore beside the PDF.** Count measures with wrong pitches or rhythms by eye and note the error types (accidentals, ties, tuplets, repeats, chord symbols, lyrics).
- [ ] **Step 6: Check the alto→tenor interval in music21.** Transposing written alto C by a perfect 4th up must give F, with E♭-sounding pitch equal to the tenor's. Record pass or fail.
- [ ] **Step 7: Write the findings file** with a per-PDF table (measures, flagged, hand-counted wrong) and a go/no-go: proceed with Audiveris, or try homr/oemer on the same PDFs first.
- [ ] **Step 8: Commit the findings file.** If the finding is no-go, stop and revise the spec before Task 2.

---

### Task 2: Backend scaffold

**Files:**
- Create: `apps/backend/pyproject.toml`, `apps/backend/package.json`, `apps/backend/src/backend/__init__.py`, `apps/backend/src/backend/errors.py`, `apps/backend/tests/test_errors.py`

**Interfaces:**
- Produces in `errors.py`:
  - `class BackendError(Exception)`
  - `class AudiverisNotFoundError(BackendError)`
  - `class OmrFailedError(BackendError)` with attributes `returncode: int`, `stderr: str`
  - `class NoOutputError(BackendError)`
  - `class InvalidInputError(BackendError)`

- [ ] **Step 1: Write failing `test_omr_failed_error_carries_returncode_and_stderr`** asserting `OmrFailedError(2, "boom")` has `.returncode == 2`, `.stderr == "boom"`, and is a `BackendError`.
- [ ] **Step 2: Run `apps/backend/.venv/bin/pytest apps/backend/tests/test_errors.py -v`.** Expected: FAIL (module missing).
- [ ] **Step 3: Create the package** with `pyproject.toml` (src layout, `pytest` with `pythonpath = ["src"]`, dependencies `music21`), a `package.json` whose `test` script runs the venv pytest, and `errors.py` per the Interfaces.
- [ ] **Step 4: Re-run the test.** Expected: PASS.
- [ ] **Step 5: Commit.**

---

### Task 3: Locate Audiveris

**Files:**
- Create: `apps/backend/src/backend/audiveris_locator.py`, `apps/backend/tests/test_audiveris_locator.py`

**Interfaces:**
- Consumes: `AudiverisNotFoundError` (Task 2). Default install paths from the Task 1 findings.
- Produces: `find_audiveris(override: Path | None = None) -> Path`. Order: explicit `override`, env var `AUDIVERIS_PATH`, `audiveris` on `PATH`, known install dirs. Raises `AudiverisNotFoundError` naming every place searched.

- [ ] **Step 1: Write failing tests** using `tmp_path` and `monkeypatch`: `test_override_wins_over_env_and_path`, `test_env_var_used_when_no_override`, `test_path_lookup_used_last`, `test_override_pointing_at_missing_file_raises`, `test_nothing_found_raises_and_lists_searched_locations`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement `find_audiveris`** with `shutil.which` for the PATH step. An override that doesn't exist raises; it never falls through to the other sources.
- [ ] **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: Commit.**

---

### Task 4: Extract MusicXML from `.mxl`

**Files:**
- Create: `apps/backend/src/backend/mxl.py`, `apps/backend/tests/test_mxl.py`

**Interfaces:**
- Consumes: `InvalidInputError` (Task 2).
- Produces: `extract_musicxml(mxl: Path, dest_dir: Path) -> Path`. Reads `META-INF/container.xml`, takes the first `rootfile@full-path`, writes it as `<mxl stem>.musicxml` in `dest_dir`, returns that path.

- [ ] **Step 1: Write failing tests** that build a zip fixture in `tmp_path`: `test_extracts_rootfile_named_in_container`, `test_output_named_after_mxl_stem` (including a Hebrew stem), `test_not_a_zip_raises_invalid_input`, `test_missing_container_raises_invalid_input`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement with `zipfile` and `xml.etree.ElementTree`.** Create `dest_dir` if missing.
- [ ] **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: Commit.**

---

### Task 5: Run Audiveris

**Files:**
- Create: `apps/backend/src/backend/omr.py`, `apps/backend/tests/test_omr.py`, `apps/backend/tests/fake_audiveris.py` (a tiny script the tests use as the "executable")

**Interfaces:**
- Consumes: `OmrFailedError`, `NoOutputError`, `InvalidInputError` (Task 2). Output naming and multi-file behaviour from Task 1.
- Produces: `run_omr(pdf: Path, out_dir: Path, audiveris: Path, timeout_s: int = 600) -> list[Path]`. Runs `[audiveris, "-batch", "-export", "-output", out_dir, "--", pdf]`, returns the `.mxl` files produced by this run, sorted. Raises `InvalidInputError` if `pdf` is missing or not `.pdf`, `OmrFailedError` on non-zero exit or timeout (process killed), `NoOutputError` if exit 0 with no `.mxl`.

- [ ] **Step 1: Write failing tests** driving `fake_audiveris.py` (modes: writes one `.mxl`, writes two, exits 3, writes nothing, sleeps): `test_returns_mxl_files_sorted`, `test_nonzero_exit_raises_with_stderr`, `test_exit_zero_without_output_raises_no_output`, `test_timeout_kills_process_and_raises`, `test_missing_pdf_raises_before_launching`, `test_non_pdf_extension_raises`, `test_path_with_spaces_and_hebrew_name_is_passed_intact`, `test_stale_mxl_from_previous_run_not_returned`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement with `subprocess.run(..., timeout=, capture_output=True, text=True, encoding="utf-8")`.** To exclude stale results, snapshot `.mxl` mtimes in `out_dir` before the run and return only files new or modified after it.
- [ ] **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: Commit.**

---

### Task 6: Orchestration and CLI

**Files:**
- Create: `apps/backend/src/backend/convert.py`, `apps/backend/src/backend/cli.py`, `apps/backend/src/backend/__main__.py`, `apps/backend/tests/test_convert.py`, `apps/backend/tests/test_cli.py`, `apps/backend/tests/test_integration_sheets.py`

**Interfaces:**
- Consumes: `find_audiveris`, `run_omr`, `extract_musicxml`, `BackendError`.
- Produces:
  - `convert_pdf(pdf: Path, out_dir: Path, audiveris: Path | None = None) -> list[Path]` — returns the `.musicxml` paths, one per movement.
  - `main(argv: list[str] | None = None) -> int` — `python -m backend convert <pdf> [--out DIR] [--audiveris PATH]`. Prints each output path on stdout, errors on stderr, returns 0 on success and 1 on any `BackendError`. Default `--out` is a folder next to the PDF named after its stem.

- [ ] **Step 1: Write failing unit tests** with `run_omr` and `find_audiveris` monkeypatched: `test_convert_returns_musicxml_for_each_mxl`, `test_convert_uses_override_path`, `test_cli_prints_paths_and_returns_zero`, `test_cli_returns_one_and_prints_error_on_backend_error`, `test_cli_default_out_dir_is_beside_pdf`.
- [ ] **Step 2: Write the integration test** `test_each_sample_pdf_converts_and_parses`, parametrized over `sheets/*.pdf`, skipped when `find_audiveris` raises, asserting the output loads with `music21.converter.parse` and has at least one measure.
- [ ] **Step 3: Run the unit tests.** Expected: FAIL.
- [ ] **Step 4: Implement `convert_pdf`, `main` and `__main__.py`.**
- [ ] **Step 5: Run the full suite.** Expected: unit tests PASS, integration PASS (or SKIPPED without Audiveris).
- [ ] **Step 6: Run `apps/backend/.venv/bin/python -m backend convert sheets/funk-out-alto-saxophone.pdf`** and open the result in MuseScore. Expected: loads and looks like the PDF.
- [ ] **Step 7: Commit.**

---

## Self-review

- **Spec coverage:** Phase 0 → Task 1 (including the interval check, C6). Phase 1 → Tasks 2–6 (locator, subprocess, errors, tests, exit criterion in Task 6 Step 6). Phases 2–5 are intentionally out of scope.
- **Type consistency:** `find_audiveris` → `Path`; `run_omr` takes that `Path`; `extract_musicxml` takes an `.mxl` `Path`; `convert_pdf` chains all three; error names match across tasks.
- **Review Focus:** each of the five lines has a named test in Tasks 5–6 (path encoding, bad input, no output, timeout, stale files).
- **Depends on Task 1:** default install dirs (Task 3), output naming and multi-file behaviour (Task 5). If Task 1 contradicts the CLAUDE.md call shape, fix Task 5 before implementing.
- **My calls:** package named `backend` (avoids picking between Music Transpose and `doron-desktop`); env var `AUDIVERIS_PATH`; 600 s default timeout; stale-file handling by mtime snapshot.
