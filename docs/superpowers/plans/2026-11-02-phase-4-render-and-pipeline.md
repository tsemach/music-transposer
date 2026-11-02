# Phase 4: Render to PDF and One-Command Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn a transposed MusicXML into a PDF with MuseScore, and offer one pipeline function and CLI command that goes PDF → OMR → validate → transpose → PDF.

**Architecture:** Generalise the executable locator so Audiveris and MuseScore share it; add a cancellable process runner shared by OMR and render; add `render_pdf`; add a top-level `run_pipeline` with a progress callback that the later sidecar reuses.

**Tech Stack:** Python 3, MuseScore 4 CLI (AppImage on this machine), music21, pytest.

**Spec:** `docs/superpowers/specs/2026-11-02-pdf-to-musicxml-design.md` (Phase 4). Probe: MuseScore AppImage exports a one-page PDF in under 1 s with `QT_QPA_PLATFORM=offscreen <AppImage> --appimage-extract-and-run -o out.pdf in.musicxml`.

## Global Constraints

- MuseScore is user-installed, never bundled; path auto-detected and overridable (CLAUDE.md).
- Same code rules as earlier phases: files under ~300 lines, no needless comments, 80/20 tests, UTF-8 paths (Hebrew names).
- Cancellation (CLAUDE.md sidecar rule): a running Audiveris/MuseScore subprocess can be killed from another thread.
- Never overwrite an input file. Output PDF must end in `.pdf`.
- Progress stages reported by the pipeline: `omr`, `validate`, `transpose`, `render`, each with a 0–100 percentage.

## Review Focus

- MuseScore missing, exits non-zero, exits 0 without a PDF, or a stale PDF from an earlier run sits at the output path: each gives a clear error, never a false success.
- Cancelling mid-run kills the child process and raises a distinct `CancelledError`; a cancel set before start never launches the process.
- Title page shows a readable title (not the file name with `.musicxml`) and no "Music21" composer.
- Output paths with spaces / Hebrew; output dir that doesn't exist yet.
- Validation errors stop the pipeline before rendering unless forced; warnings pass through to the result.

## File Structure

- `backend/executables.py` — generic `find_executable`; `audiveris_locator.py` and `musescore_locator.py` become thin wrappers.
- `backend/process.py` — `run_process` with timeout and cancel.
- `backend/render.py` — `render_pdf`.
- `backend/pipeline.py` — `run_pipeline`, `PipelineResult`.
- `backend/errors.py`, `backend/omr.py`, `backend/cli.py`, `backend/transpose/*` — modify.

---

### Task 1: Shared executable locator and MuseScore locator

**Files:**
- Create: `executables.py`, `musescore_locator.py`, `tests/test_musescore_locator.py`
- Modify: `audiveris_locator.py`, `errors.py`

**Interfaces:**
- Produces in `errors.py`: `class ExecutableNotFoundError(BackendError)`; `AudiverisNotFoundError` now subclasses it; new `class MuseScoreNotFoundError(ExecutableNotFoundError)`; new `class CancelledError(BackendError)`; new `class RenderFailedError(BackendError)` with `returncode: int`, `stderr: str`.
- Produces in `executables.py`: `def find_executable(label: str, env_var: str, names: tuple[str, ...], known_dirs: list[Path], error: type[ExecutableNotFoundError], override: Path | None = None) -> Path` — same order and error text as today's Audiveris locator (override, env var, PATH, known dirs; an override or env path that is missing raises, never falls through).
- Produces: `find_musescore(override: Path | None = None) -> Path` with env var `MUSESCORE_PATH`, names `("MuseScore4", "mscore4", "mscore", "musescore", "MuseScore.AppImage")`, known dirs `~/.local/opt/musescore`, `/opt/musescore`, `/usr/local/bin`, `C:/Program Files/MuseScore 4/bin`, `/Applications/MuseScore 4.app/Contents/MacOS`. `find_audiveris` keeps its signature and behaviour.

- [ ] **Step 1: Write failing tests** for `find_musescore` mirroring the Audiveris locator tests (override wins; env var; PATH; known dir under home finds `MuseScore.AppImage`; missing override raises `MuseScoreNotFoundError`; nothing found lists searched places). Existing Audiveris locator tests must keep passing unchanged.
- [ ] **Step 2: Run** `apps/backend/.venv/bin/pytest apps/backend/tests/test_musescore_locator.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `executables.py` by moving the generic logic out of `audiveris_locator.py`; both locators call it.
- [ ] **Step 4: Run the whole fast suite** (`--ignore` the three integration files). Expected: PASS.
- [ ] **Step 5: Commit.**

---

### Task 2: Cancellable process runner

**Files:**
- Create: `process.py`, `tests/test_process.py`
- Modify: `omr.py`

**Interfaces:**
- Produces: `@dataclass class ProcessResult: returncode: int; stderr: str` and `def run_process(command: list[str], timeout_s: int, cancel: threading.Event | None = None, env: dict[str, str] | None = None) -> ProcessResult`. Starts the child with `Popen`, polls every ≤0.2 s; on `cancel.is_set()` kills it and raises `CancelledError`; on timeout kills it and raises `TimeoutError`-equivalent `OmrFailedError`-agnostic `subprocess.TimeoutExpired` (callers translate); a cancel already set before start raises `CancelledError` without launching.
- `omr.run_omr` gains a keyword `cancel: threading.Event | None = None` and uses `run_process`; its timeout error and all existing behaviour stay.

- [ ] **Step 1: Write failing tests** using a tiny `sys.executable -c` child: `test_returns_exit_code_and_stderr`, `test_timeout_kills_child_and_raises`, `test_cancel_during_run_kills_child_and_raises_cancelled` (set the event from a timer thread after 0.3 s; the child sleeps 30 s; the call returns in under 5 s), `test_cancel_set_before_start_never_launches` (child would create a marker file), `test_env_is_passed_to_child`. In `test_omr.py` add `test_cancel_kills_audiveris_and_raises_cancelled` with the fake in `sleep` mode.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement `run_process`** and switch `run_omr` to it.
- [ ] **Step 4: Run the fast suite.** Expected: PASS.
- [ ] **Step 5: Commit.**

---

### Task 3: Render to PDF

**Files:**
- Create: `render.py`, `tests/fake_musescore.py`, `tests/test_render.py`

**Interfaces:**
- Consumes: `run_process`, `RenderFailedError`, `InvalidInputError`, `CancelledError`.
- Produces: `def render_pdf(musicxml: Path, out_pdf: Path, musescore: Path, timeout_s: int = 120, cancel: threading.Event | None = None) -> Path`. Command is `[musescore, ("--appimage-extract-and-run" when the file name ends with .AppImage), "-o", out_pdf, musicxml]` with env `QT_QPA_PLATFORM=offscreen` added on Linux. Raises `InvalidInputError` when `musicxml` is missing or `out_pdf` lacks a `.pdf` suffix or equals `musicxml`; deletes any existing `out_pdf` before running (so a stale file can't pass); `RenderFailedError` on non-zero exit or timeout; `RenderFailedError` when exit 0 but no PDF appears. Creates the output directory.

- [ ] **Step 1: Write failing tests** against `fake_musescore.py` (modes: writes PDF; exits 4 with stderr; exits 0 writing nothing; sleeps): `test_writes_pdf_and_returns_path`, `test_nonzero_exit_raises_with_stderr`, `test_exit_zero_without_pdf_raises`, `test_stale_pdf_not_accepted`, `test_missing_musicxml_raises_before_launching`, `test_non_pdf_output_name_raises`, `test_path_with_spaces_and_hebrew_name`, `test_appimage_name_adds_extract_and_run_flag` (fake named `MuseScore.AppImage` records its args), `test_cancel_raises_cancelled`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement `render_pdf`.**
- [ ] **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: Commit.**

---

### Task 4: Title and composer metadata

**Files:**
- Modify: `transpose/transposer.py`, `transpose/pipeline.py`
- Test: `tests/transpose/test_transposer.py`, `tests/transpose/test_pipeline.py`

**Interfaces:**
- `transpose_score(score, source, register="auto", title: str | None = None)`: when `title` is given it becomes `score.metadata.title` / `movementName`; the default `Music21` composer is removed.
- `transpose_musicxml(..., title: str | None = None)`: default title is the source file stem with `-`/`_` replaced by spaces and the instrument words `alto`, `tenor`, `sax`, `saxophone` dropped, then title-cased (`gymnopedie-no-1-alto-saxophone` → `Gymnopedie No 1`).

- [ ] **Step 1: Write failing tests:** `test_title_written_and_music21_composer_removed` (written XML contains the title and no `Music21`), `test_default_title_from_file_stem` (the Gymnopedie example above), `test_explicit_title_overrides_default`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the fast suite.** Expected: PASS.
- [ ] **Step 5: Commit.**

---

### Task 5: Pipeline function and CLI

**Files:**
- Create: `pipeline.py`, `tests/test_pipeline.py`, `tests/test_integration_full_pipeline.py`
- Modify: `cli.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `find_audiveris`, `find_musescore`, `convert_pdf`, `transpose_musicxml`, `render_pdf`.
- Produces: `ProgressCallback = Callable[[str, int], None]`; `@dataclass class PipelineResult: original_musicxml: Path; tenor_musicxml: Path; pdf: Path; interval: ChosenInterval; report: ValidationReport; warnings: list[str]`; `def run_pipeline(pdf: Path, out_dir: Path, source: SaxophoneKind, register: Register = "auto", force: bool = False, audiveris: Path | None = None, musescore: Path | None = None, on_progress: ProgressCallback | None = None, cancel: threading.Event | None = None) -> PipelineResult`. Outputs in `out_dir`: `<stem>.musicxml` (OMR), `<stem>.<target>.musicxml`, `<stem>.<target>.pdf`. Progress at stage starts: `("omr", 5)`, `("validate", 55)`, `("transpose", 65)`, `("render", 80)`, then `("done", 100)`. A validation failure raises `ValidationFailedError` before `transpose`/`render`. More than one movement from OMR: first used, warning added.
- CLI: `run <pdf> --from {alto,tenor} [--register ...] [--out-dir DIR] [--force] [--audiveris P] [--musescore P]`; prints the PDF path on stdout, progress lines, interval and warnings on stderr; default out dir is the folder next to the PDF named after its stem.

- [ ] **Step 1: Write failing tests** with the collaborators monkeypatched: `test_stages_reported_in_order`, `test_validation_failure_stops_before_render`, `test_force_continues_past_validation_errors`, `test_extra_movements_add_warning`, `test_paths_named_after_stem_and_target`; CLI: `test_run_prints_pdf_path_and_progress`, `test_run_validation_failure_exits_one`.
- [ ] **Step 2: Write the integration test** `test_full_pipeline_on_gymnopedie` (skipped without Audiveris, MuseScore or the sheet): result PDF exists, starts with `%PDF`, is larger than 5 kB, interval register is `same`.
- [ ] **Step 3: Run the unit tests.** Expected: FAIL.
- [ ] **Step 4: Implement `run_pipeline` and the CLI command.**
- [ ] **Step 5: Run the full suite.** Expected: PASS.
- [ ] **Step 6: Run `python -m backend run sheets/gymnopedie-no-1-alto-saxophone.pdf --from alto --out-dir <scratch>`** and inspect the PDF as an image (PyMuPDF in the scratch venv): tenor part, readable title, no "Music21". Expected: exit 0.
- [ ] **Step 7: Commit.**

---

## Self-review

- **Spec coverage:** Phase 4 asks for MusicXML → PDF via MuseScore (Tasks 1, 3, 5) and a CLI `--pdf` equivalent (Task 5 `run`). Verovio preview is a UI concern and moves to the desktop plan.
- **Added beyond the spec:** cancellation (CLAUDE.md sidecar rule) and metadata clean-up (found in the Phase 3 render).
- **Type consistency:** `run_process` is used by `run_omr` and `render_pdf`; `CancelledError` raised in `process.py` only; `PipelineResult.interval` is the Phase 3 `ChosenInterval`.
- **Review Focus:** each line has a named test (Tasks 2, 3, 4, 5).
- **My calls:** env var `MUSESCORE_PATH`; first movement only; default title derived from the file stem; pipeline outputs sit beside each other in one folder.
