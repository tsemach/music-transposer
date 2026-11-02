# Music Transposer — Project Context

Desktop app that takes sheet music as **PDF**, transposes it to a new key, and outputs a new **PDF**.
Internally everything goes through **MusicXML**.

## Pipeline

```
PDF ──▶ page images ──▶ OMR (AI) ──▶ MusicXML ──▶ validate/fix ──▶ transpose ──▶ MusicXML ──▶ render ──▶ PDF
```

1. **PDF → images**: PyMuPDF (render at 300+ DPI).
2. **OMR (images → MusicXML)**: Audiveris is the main candidate (most mature, CLI batch mode).
   Alternatives: homr / oemer (Python deep-learning OMR). Not finalized — benchmark on real sheets first.
   - Audiveris ≥ 5.5 installers bundle their own Java runtime; no separate Java install needed.
   - Call it as a subprocess: `audiveris -batch -export -output <dir> -- <file.pdf>` → produces `.mxl`.
   - License is **AGPLv3**: fine for personal use; check before bundling/distributing commercially.
     Audiveris is NOT bundled in our installer — user installs it; backend auto-detects path, overridable in settings.
3. **Validate**: music21 — check measure durations vs time signature, flag suspicious results.
   An LLM may assist with repairs, but OMR output stays the source of truth; user review step is important.
4. **Transpose**: music21 (`score.transpose(...)`). Care points: key signature, enharmonic spelling,
   chord symbols, octave/clef adjustment for instrument range.
5. **Render MusicXML → PDF**: MuseScore CLI (`mscore -o out.pdf in.musicxml`), best engraving.
   Fallbacks: Verovio, LilyPond. MuseScore is installed by the user, not bundled.
   Note: output is re-engraved, so layout will differ from the original.

Expected weak spots: scans/phone photos, handwriting, multiple voices per staff, tuplets, ties vs slurs,
lyrics, chord symbols, dense piano music.

## Stack & repo layout

- **Monorepo**: Turborepo + **pnpm**.
- **apps/desktop**: Tauri v2 app (frontend React + TS). Verovio (JS/WASM) for in-app score preview
  (before/after transposition, and for the review-and-fix step).
- **apps/backend**: Python backend, packaged with **PyInstaller** (`--onefile`) as a Tauri **sidecar**.
  Its `package.json` `build` script runs PyInstaller so Turbo builds it before the desktop app.
- Sidecar binary goes in `apps/desktop/src-tauri/binaries/` with target-triple suffix,
  e.g. `backend-x86_64-pc-windows-msvc.exe`; registered via `bundle.externalBin: ["binaries/backend"]`.
- Tauri shell plugin (`tauri-plugin-shell`, `@tauri-apps/plugin-shell`); capability:
  `{ "identifier": "shell:allow-spawn", "allow": [{ "name": "binaries/backend", "sidecar": true }] }`.
- PyInstaller only builds for the host OS → build per platform (CI).

## Sidecar protocol (UI ⇄ Python)

Long-lived process, spawned once at app start. **Newline-delimited JSON** over stdin/stdout.

- stdin  (UI → Python): requests `{"id": 7, "cmd": "transpose", "pdf": "C:/...", "interval": "M2"}`
- stdout (Python → UI): **protocol messages only**
  - `{"type": "ready", "version": "0.1"}` once at startup — UI waits for it before sending.
  - `{"id": 7, "type": "progress", "stage": "omr", "pct": 40}` (zero or more)
  - `{"id": 7, "type": "result", "pdf": "..."}` or `{"id": 7, "type": "error", "message": "..."}` (exactly one)
- stderr: logs only, never parsed.

Rules:
- Every request has an `id`; every reply echoes it.
- Pass **file paths**, never file contents.
- Python: keep the real stdout for protocol, set `sys.stdout = sys.stderr` so stray prints
  (incl. from music21) can't corrupt the stream; flush after every message; guard writes with a lock.
- Force **UTF-8** on stdin/stdout (`reconfigure(encoding="utf-8")`, `ensure_ascii=False`) — Hebrew file names on Windows.
- Each request handled in its own thread so the read loop stays free (supports a `cancel` cmd that kills the
  running Audiveris subprocess).
- Lifecycle: when Tauri exits, stdin closes → Python's `for line in sys.stdin` loop ends → process exits.
  UI listens to `close` to reject pending calls and optionally restart the backend.
- UI side: a `Backend` class wrapping `Command.sidecar('binaries/backend')`, with a pending-requests map
  so the app can `await backend.call('transpose', {...}, onProgress)`.

## Turbo config notes

Root `turbo.json`:
```json
{
  "tasks": {
    "build": { "dependsOn": ["^build"], "outputs": ["dist/**", "src-tauri/target/release/**"] },
    "dev": { "cache": false, "persistent": true }
  }
}
```
Run the app: `pnpm turbo dev --filter desktop`.

## Suggested first milestone

A Python CLI prototype of the full pipeline (PDF → OMR → music21 transpose → MuseScore → PDF),
tested on a handful of real sheets to measure OMR accuracy, before building out the Tauri UI.

## Open questions

- Are the input sheets mostly clean digital PDFs or scans/photos? (Affects OMR choice.)
- Personal use vs distributed product? (Decides whether Audiveris's AGPL is acceptable.)
