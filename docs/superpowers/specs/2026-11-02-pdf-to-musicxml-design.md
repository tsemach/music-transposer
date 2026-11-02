# Ascurix — PDF → MusicXML, then alto↔tenor conversion (Design)

Status: draft for approval. Companion to `CLAUDE.md`, which holds the stack and sidecar protocol; this doc does not repeat them.

## Intent

Take a sheet-music PDF of a single saxophone part (reference input: `funk-out-alto-saxophone.pdf`), turn it into MusicXML, and operate on that MusicXML. The first operation is converting an alto sax part (E♭) to a tenor sax part (B♭) and back, so the part sounds the same on the other instrument.

The hard part is PDF → MusicXML. Everything after it is comparatively mechanical, but inherits every OMR error silently. So the early phases are about getting MusicXML we can trust, and knowing when we can't.

## Goals

- G1. CLI: `PDF in → MusicXML out`, one command, on the reference PDF and similar clean digital parts.
- G2. A validation report that says which measures look wrong, so a human knows where to look.
- G3. Alto↔tenor part conversion on that MusicXML, with correct key signature, spelling and octave choice.
- G4. Minimal UI last: upload PDF, pick operation, download result.

## Non-goals (v1)

- Scans, phone photos, handwriting, dense piano music.
- Arbitrary-key transposition UI, or other operations beyond alto↔tenor (the interval engine underneath is generic; no UI for it).
- Matching the original PDF layout. Output is re-engraved.
- Bundling Audiveris or MuseScore in the installer.
- Cross-platform packaging and CI.

## Anti-goals

- A tool that outputs a plausible-looking but wrong tenor part with no warning. A loud "bars 12, 19 failed validation" beats a silent wrong note.
- Hiding OMR output behind an LLM "fix". OMR output stays the source of truth (per CLAUDE.md).

## Constraints

- From CLAUDE.md: MusicXML is the internal format; music21 for validate/transpose; Audiveris is the main OMR candidate, AGPLv3, user-installed; MuseScore CLI for rendering; Python backend in `apps/backend`; Tauri desktop app later.
- Repo today is the stock create-turbo template (`apps/web`, `apps/docs`). No desktop or backend app exists yet.
- Dev machine is WSL2 (Linux). None of Audiveris, MuseScore, Java, poppler or PyMuPDF were installed when this was written. The `python3` on PATH is `/usr/local/bin/python3`.
- Project rules: files under ~300 lines, no comments by default, tests follow 80/20, plan before code.

## Decisions made by the user

- Focus on PDF → MusicXML first; operations come after.
- Minimal UI; CLI first.
- Operation of interest is alto↔tenor conversion (not general key change).

## Decisions made by me (calls, please check)

- C1. **Skip the separate PDF→image step for Audiveris.** Audiveris reads PDFs directly. CLAUDE.md step 1 (PyMuPDF at 300 DPI) is only needed if we fall back to homr/oemer or want page previews. Keep it out of Phase 1.
- C2. **Phase 0 is a throwaway spike**, no product code, to decide the OMR engine on real evidence before building around it.
- C3. **Python package in `apps/backend` with a CLI entry point first**; the sidecar protocol loop is added in Phase 5 on top of the same functions.
- C4. **Source instrument is an explicit input** (`--from alto|tenor`), cross-checked against the MusicXML part name / transposition tag if present. OMR doesn't reliably detect it.
- C5. **Octave choice is automatic from the part's range, with an override flag.**
- C6. Alto→tenor interval: written up a perfect 4th (or down a perfect 5th). Derived by hand; **must be confirmed against music21 in Phase 0** before anything depends on it.

## Phases

Each phase has an exit criterion; don't start the next without it.

### Phase 0 — Spike (throwaway)

- Install Audiveris and MuseScore on the dev machine; record versions and how they were installed (WSL2 headless MuseScore may need an offscreen/xvfb setup — unverified).
- Run Audiveris on the reference PDF; open the `.mxl` in MuseScore and compare to the PDF by eye.
- Run music21 on the output: load, count measures, check durations, read the part's instrument/transposition.
- Verify the alto→tenor interval with music21 on a few notes.
- **Exit:** a short written finding: is Audiveris output good enough to build on (rough % of correct measures), what kinds of errors appear, and is the interval confirmed. If not good enough, try homr/oemer on the same PDF before proceeding.

### Phase 1 — PDF → MusicXML CLI

- `apps/backend` Python package with a `convert` command: locate Audiveris (auto-detect, overridable), run it as a subprocess, unzip `.mxl` to `.musicxml`, surface Audiveris's stderr and exit code.
- Errors: Audiveris missing, non-zero exit, no output produced, multiple movements/parts in output.
- Tests: one happy-path test against the reference PDF (skipped when Audiveris isn't installed), one failure test with a bad path.
- **Exit:** `convert funk-out-alto-saxophone.pdf` produces a MusicXML file that loads in music21 and MuseScore.

### Phase 2 — Validate

- music21 checks: measure duration vs time signature (allowing pickup and final bar), part/instrument present, key and time signature present, suspicious items (very short rests, empty measures).
- Output: a report listing flagged measure numbers and the reason; non-zero exit option for CI.
- Tests: crafted MusicXML fixtures with known-bad measures.
- **Exit:** report on the reference PDF matches what a human sees when comparing to the PDF.

### Phase 3 — Alto↔tenor conversion

- Interval engine in music21; alto↔tenor wrapper using C4–C6.
- Cover: key signature change, enharmonic spelling, chord symbols, range check with automatic octave and override.
- Tests: small hand-written scores with expected output; round-trip alto→tenor→alto is identity.
- **Exit:** reference part converts to a tenor part that opens in MuseScore, sounds the same when played back against the original (checked by ear/MuseScore concert pitch view).

### Phase 4 — Render and preview

- MusicXML → PDF via MuseScore CLI; Verovio for preview if the UI needs it.
- **Exit:** CLI `--pdf` flag produces a readable tenor PDF.

### Phase 5 — Minimal UI

- Tauri app, sidecar per CLAUDE.md protocol: upload PDF, choose alto→tenor or tenor→alto, progress, show validation flags, download MusicXML/PDF.
- **Exit:** the Phase 3 flow works end to end from the UI.

## Risks

- OMR accuracy on the reference PDF is unknown. Mitigation: Phase 0 before any commitment.
- Audiveris AGPL if the product is ever distributed (still an open question in CLAUDE.md).
- Silent errors passing through conversion. Mitigation: Phase 2 gate; the CLI refuses to convert flagged measures without `--force`.
- WSL2 environment friction for MuseScore/Audiveris. Mitigation: record exact install steps in Phase 0.

## Left to the builder

- Package layout inside `apps/backend`, CLI library (argparse vs typer), test runner config.
- How to detect Audiveris paths per OS.
- Exact thresholds for "suspicious" in validation.

## Open questions

- Will this ever be distributed or sold? (Decides what to do about AGPL.)
- Benchmark set is the three alto sax PDFs in `sheets/` (`amazing-grace-alto-sax.pdf`, `funk-out-alto-saxophone.pdf`, `gymnopedie-no-1-alto-saxophone.pdf`). Small, so likely vector exports, but unverified. Three files is still a thin test set; more from different publishers would help.
