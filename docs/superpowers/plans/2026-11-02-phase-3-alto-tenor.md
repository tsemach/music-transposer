# Phase 3: Alto ↔ Tenor Conversion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn an alto sax MusicXML part into a tenor sax part (and back) that sounds the same or an octave away, chosen by what fits the instrument's written range.

**Architecture:** A `backend.transpose` subpackage: instrument facts, register (octave) choice, the music21 transposition itself, and a file-level pipeline that applies the Phase 2 validation gate. The CLI gets a `transpose` command.

**Tech Stack:** Python 3, music21, pytest.

**Spec:** `docs/superpowers/specs/2026-11-02-pdf-to-musicxml-design.md` (Phase 3, calls C4–C6). Evidence: `docs/superpowers/findings/2026-11-02-omr-spike.md` and the probe results below.

## Global Constraints

- Intervals (spec C6, confirmed in the spike): alto→tenor "same sound" is written **up a perfect 4th**; "shifted" (an octave lower in sound) is **down a perfect 5th**. Tenor→alto "same sound" is **down a P4**; "shifted" (an octave higher in sound) is **up a P5**.
- Written range for both instruments: **B♭3 to F6** (my call; constants in one place).
- The source instrument is always an explicit input (spec C4); OMR cannot supply it.
- Register is automatic by default: the candidate with the fewest out-of-range written notes wins, ties go to "same sound" (spec C5); `--register same|shifted` overrides.
- Phase 2 gate: validation errors refuse the conversion and write nothing unless forced; warnings never block (my call, spec leaves it open).
- Never overwrite the input file. Files under ~300 lines, no needless comments, 80/20 tests.

## Probe results this plan relies on (music21 10.5.2, real Audiveris output)

- `score.transpose("P4")` transposes existing key signatures, but a score with no `<key>` at bar 1 (C major, which Audiveris omits) gets **no** key signature after transposing: the notes just get accidentals. Insert `KeySignature(0)` first.
- Out-of-range counts (of 132 / 135 / 71 notes), alto→tenor: Gymnopédie up P4 = 0, down P5 = 18; Amazing Grace up P4 = 16, down P5 = 0; Funk Out up P4 = 0, down P5 = 1.
- Setting the part's instrument to `TenorSaxophone()` and writing MusicXML emits `<transpose><diatonic>-1</diatonic><chromatic>-2</chromatic><octave-change>-1</octave-change></transpose>`.

## Review Focus

- Score with no key signature at bar 1: output has the transposed signature at bar 1, not accidentals only.
- Notes out of range under both candidates: still converts, picks the fewer-violations candidate, reports the count.
- Chords, rests and ties: chords transposed pitch by pitch, ties and rests preserved.
- `--from alto` on a part named "Tenor Saxophone" (or the reverse): a warning, not silence.
- Validation errors without force: nothing written and the findings listed; output path equal to input path: refused.

## File Structure

- `apps/backend/src/backend/transpose/saxophones.py` — kinds, range, interval table, instruments.
- `apps/backend/src/backend/transpose/register.py` — interval choice.
- `apps/backend/src/backend/transpose/transposer.py` — `transpose_score`.
- `apps/backend/src/backend/transpose/pipeline.py` — file-level pipeline.
- `apps/backend/src/backend/transpose/__init__.py` — exports.
- `apps/backend/src/backend/errors.py`, `cli.py` — modify.
- `apps/backend/tests/transpose/` — tests, with a score-building helper alongside.

---

### Task 1: Saxophone facts

**Files:**
- Create: `transpose/__init__.py` (empty for now), `transpose/saxophones.py`, `tests/transpose/test_saxophones.py`

**Interfaces:**
- Produces in `saxophones.py`:
  - `SaxophoneKind = Literal["alto", "tenor"]`; `Register = Literal["auto", "same", "shifted"]`
  - `WRITTEN_LOW_PS: float` and `WRITTEN_HIGH_PS: float` (MIDI numbers of B♭3 and F6)
  - `def target_of(source: SaxophoneKind) -> SaxophoneKind`
  - `def interval_name(source: SaxophoneKind, register: Literal["same", "shifted"]) -> str` returning `"P4"`, `"-P5"`, `"-P4"`, `"P5"` per the Global Constraints
  - `def instrument_for(kind: SaxophoneKind) -> instrument.Instrument` (music21 `AltoSaxophone` / `TenorSaxophone`) and `def part_name_for(kind) -> str` (`"Alto Saxophone"` / `"Tenor Saxophone"`)

- [ ] **Step 1: Write failing tests:** `test_target_of_swaps_kind`, `test_interval_names_for_all_four_combinations`, `test_same_sound_interval_round_trips_to_original_pitch` (C4 alto → tenor via `interval_name`, then tenor → alto, back to C4), `test_instruments_carry_saxophone_transposition` (tenor: chromatic −14; alto: chromatic −9).
- [ ] **Step 2: Run** `apps/backend/.venv/bin/pytest apps/backend/tests/transpose/test_saxophones.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `saxophones.py`.**
- [ ] **Step 4: Run again.** Expected: PASS.
- [ ] **Step 5: Commit.**

---

### Task 2: Register choice

**Files:**
- Create: `transpose/register.py`, `tests/transpose/score_helpers.py`, `tests/transpose/test_register.py`

**Interfaces:**
- Consumes: Task 1.
- Produces in `register.py`:
  - `@dataclass(frozen=True) class ChosenInterval: name: str; register: Literal["same", "shifted"]; out_of_range: int`
  - `def choose_interval(score: stream.Score, source: SaxophoneKind, register: Register = "auto") -> ChosenInterval`. For each candidate it counts written pitches (every pitch of every note and chord) that would fall outside `WRITTEN_LOW_PS..WRITTEN_HIGH_PS` after transposing; `auto` takes the lowest count, tie → `"same"`; an explicit register is used as given, still reporting its count.
- Produces in `score_helpers.py` (tests only): `def make_score(pitches: list[str], key_fifths: int | None = None) -> stream.Score` — one part, 4/4, one quarter note per pitch, optional initial `KeySignature`.

- [ ] **Step 1: Write failing tests:** `test_auto_picks_same_sound_when_it_fits`, `test_auto_picks_shifted_when_same_sound_goes_too_high` (alto with a written D6: up P4 = G6 out, down P5 = G5 in), `test_tie_goes_to_same_sound` (empty-ish score), `test_both_out_of_range_picks_fewer_and_reports_count`, `test_explicit_register_overrides_auto_but_reports_count`, `test_chord_pitches_all_counted`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement `choose_interval`** (use `pitch.Pitch.ps` plus the interval's semitones; no actual transposition needed for counting).
- [ ] **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: Commit.**

---

### Task 3: Transpose a score

**Files:**
- Create: `transpose/transposer.py`, `tests/transpose/test_transposer.py`

**Interfaces:**
- Consumes: `choose_interval`, `ChosenInterval`, `instrument_for`, `part_name_for`, `target_of`, `make_score`.
- Produces: `@dataclass class TransposeResult: score: stream.Score; interval: ChosenInterval` and `def transpose_score(score: stream.Score, source: SaxophoneKind, register: Register = "auto") -> TransposeResult`. Behaviour: if the first measure has no `KeySignature`, insert `KeySignature(0)` into a copy first; transpose by the chosen interval; replace the part's instrument with the target saxophone and set `partName`; never mutate the input score.

- [ ] **Step 1: Write failing tests:** `test_no_key_signature_gets_transposed_one_at_bar_one` (C major alto→tenor: first key signature has −1 sharps), `test_existing_key_signature_is_transposed` (2 flats + P4 → 3 flats), `test_notes_transposed_by_chosen_interval_with_chords_and_ties` (chord and a tie preserved), `test_instrument_and_part_name_replaced_with_target`, `test_input_score_not_mutated`, `test_alto_to_tenor_then_back_restores_pitches_and_key` (same-sound both ways), `test_written_musicxml_declares_target_transposition` (write to a temp file; the XML contains `<chromatic>-2</chromatic>` and `<octave-change>-1</octave-change>` for tenor).
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement `transpose_score`.**
- [ ] **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: Commit.**

---

### Task 4: File pipeline with the validation gate

**Files:**
- Create: `transpose/pipeline.py`, `tests/transpose/test_pipeline.py`
- Modify: `transpose/__init__.py` (export `transpose_musicxml`), `errors.py`

**Interfaces:**
- Consumes: `validate_musicxml`, `ValidationReport`, `transpose_score`, `InvalidInputError`, the Phase 2 fixture builder `make_musicxml`.
- Produces:
  - In `errors.py`: `class ValidationFailedError(BackendError)` with attribute `report: ValidationReport`; its message lists the error findings.
  - `@dataclass class TransposeOutcome: out_path: Path; interval: ChosenInterval; report: ValidationReport; warnings: list[str]`
  - `def transpose_musicxml(source_path: Path, out_path: Path, source: SaxophoneKind, register: Register = "auto", force: bool = False) -> TransposeOutcome`. Order: refuse if `out_path` resolves to `source_path` (`InvalidInputError`); validate; if the report has errors and not `force`, raise `ValidationFailedError` before writing anything; parse, transpose, write MusicXML to `out_path`. `warnings` collects: out-of-range count if non-zero, and a declared-instrument conflict (part or instrument name containing "tenor"/"alto" that disagrees with `source`).

- [ ] **Step 1: Write failing tests** (fixtures from `make_musicxml`): `test_clean_file_is_written_and_parses`, `test_validation_errors_refuse_and_write_nothing`, `test_force_converts_despite_errors`, `test_warnings_only_does_not_block`, `test_output_equal_to_input_refused`, `test_out_of_range_count_reported_as_warning`, `test_part_named_tenor_with_from_alto_warns`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement the pipeline and the new error.**
- [ ] **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: Commit.**

---

### Task 5: CLI and real-sheet integration

**Files:**
- Modify: `cli.py`, `tests/test_cli.py`
- Create: `tests/transpose/test_integration_sheets_transpose.py`

**Interfaces:**
- Consumes: `transpose_musicxml`, `TransposeOutcome`, `ValidationFailedError`.
- Produces: CLI `transpose <musicxml> --from {alto,tenor} [--register {auto,same,shifted}] [--out FILE] [--force]`. Default output: `<stem>.<target>.musicxml` beside the input. Prints the output path on stdout; the chosen interval and each warning on stderr; `ValidationFailedError` prints its findings to stderr and exits 1; other `BackendError` exits 1.

- [ ] **Step 1: Write failing CLI tests** (monkeypatch `cli.transpose_musicxml`): `test_transpose_prints_path_and_reports_interval_on_stderr`, `test_transpose_default_output_name_uses_target_kind`, `test_transpose_validation_failure_lists_findings_and_exits_one`, `test_transpose_passes_register_and_force_flags`.
- [ ] **Step 2: Write the integration test** `test_sample_sheets_choose_expected_register`, skipped without Audiveris or sheets: convert each sample, transpose alto→tenor (`force=True` for Amazing Grace, which has the known bar-34 error), and assert Gymnopédie and Funk Out chose `same` with 0 out of range, Amazing Grace chose `shifted` with 0 out of range, all outputs re-parse in music21, and transposing back with the matching register restores the original pitches.
- [ ] **Step 3: Run the unit tests.** Expected: FAIL.
- [ ] **Step 4: Implement the CLI command.**
- [ ] **Step 5: Run the full suite.** Expected: all pass.
- [ ] **Step 6: Run the real flow:** convert `sheets/gymnopedie-no-1-alto-saxophone.pdf`, then `python -m backend transpose <result.musicxml> --from alto`. Open the output in MuseScore (headless PNG export from the spike) and check by eye: tenor part, 1-flat key signature, plausible notes. Expected: exit 0 and a readable score.
- [ ] **Step 7: Commit.**

---

## Self-review

- **Spec coverage:** Phase 3 asks for an interval engine (Tasks 1–3), alto↔tenor wrapper with C4–C6 (1, 3, 4), key signature / spelling / octave choice (2, 3), range check with override (2, 5), round trip (3, 5), exit criterion "converted part opens in MuseScore" (Task 5 Step 6). Chord symbols are not exercised: none of the samples contain them. If a real part has them, music21 transposes `ChordSymbol` objects, but this plan does not test that.
- **Not covered:** concert-pitch playback comparison by ear; transposing the original (alto) file's own missing `<transpose>` tag.
- **Type consistency:** `SaxophoneKind`, `Register`, `ChosenInterval` and `TransposeResult` are used identically across Tasks 1–5; `transpose_musicxml` is the only file-level entry point.
- **Review Focus:** each of the five lines has a named test (Tasks 2–4).
- **My calls:** written range B♭3–F6; ties go to same sound; warnings never block; default output name `<stem>.<target>.musicxml`; the declared-instrument check is a warning only.
