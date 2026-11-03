# Phase 5b: Desktop App (Tauri v2 + React) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A minimal desktop window: choose a sheet-music PDF, pick alto→tenor or tenor→alto, watch progress, review validation findings, and open the resulting PDF/MusicXML.

**Architecture:** `apps/desktop` is a Tauri v2 shell around a Vite + React + TypeScript frontend. The frontend talks to the Python sidecar (Phase 5a) through a `Backend` class that depends only on a small `Transport` interface; a Tauri adapter implements it with `tauri-plugin-shell`, a mock implements it for tests and design review. The Python backend is frozen with PyInstaller into `src-tauri/binaries/backend-<target-triple>` and registered as `externalBin`.

**Tech Stack:** Tauri 2 (Rust 1.95), React 19, TypeScript, Vite 8, Vitest + Testing Library, `@tauri-apps/plugin-shell`, `plugin-dialog`, `plugin-opener`, PyInstaller. pnpm + Turborepo.

**Spec:** `CLAUDE.md` (stack, sidecar protocol, Turbo notes), `docs/superpowers/specs/2026-11-02-pdf-to-musicxml-design.md` (Phase 5), `docs/superpowers/plans/2026-11-02-phase-5a-sidecar.md` (protocol and commands).

## Global Constraints

- Product name in all UI copy and window title is **Music Transpose**. Real resources keep the old name: Tauri identifier `com.tsemach.doron-desktop`; the repo/directory name is untouched (project naming rule).
- Sidecar rules from CLAUDE.md: spawned once at app start, waits for `ready` before sending, every request has an `id`, file **paths** only, stdin closing ends it; UI rejects pending calls when it closes and offers restart.
- Capability for the sidecar: `{ "identifier": "shell:allow-spawn", "allow": [{ "name": "binaries/backend", "sidecar": true, "args": ["serve"] }] }`.
- Audiveris and MuseScore are **not** bundled; the UI shows detection status and lets the user pick the executables.
- Turbo: `apps/backend` `build` script builds the sidecar so it runs before `apps/desktop` builds; run the app with `pnpm turbo dev --filter desktop` (CLAUDE.md). Never start dev servers for the user; verification uses throwaway servers that are stopped afterwards.
- TypeScript: no `any`; types for protocol messages; files under ~300 lines; no needless comments; 80/20 tests; follow existing monorepo conventions.
- UI must be keyboard accessible, readable in light and dark, and never show a raw stack trace.

## Review Focus

- Sidecar dies mid-job: pending call rejects with a clear message, UI shows "backend stopped" with a Restart button, no stuck spinner.
- Messages split across chunks or several per chunk: parsed correctly; a non-JSON line (stray output) is ignored, not fatal.
- User picks a non-PDF or the PDF disappears: clear message, no crash.
- Validation failure: findings listed, "Convert anyway" re-runs with force; nothing implies the result is trustworthy when forced.
- Cancel during OMR returns the UI to a usable state; double-clicking Convert doesn't start two jobs.
- Hebrew file names display correctly (RTL-safe, no mojibake).

## File Structure

```
apps/desktop/
  package.json, tsconfig.json, vite.config.ts, index.html
  src/main.tsx, App.tsx, styles.css
  src/backend/protocol.ts, Backend.ts, tauriTransport.ts, mockTransport.ts
  src/state/jobReducer.ts, useBackend.ts, settings.ts
  src/lib/describeInterval.ts, fileName.ts
  src/components/*.tsx   (ToolStatus, FilePicker, ModePicker, ProgressView, FindingsList, ResultCard, ErrorBanner)
  src/__tests__/*.test.ts(x)
  src-tauri/Cargo.toml, build.rs, tauri.conf.json, capabilities/default.json, icons/, src/main.rs, src/lib.rs, binaries/ (git-ignored)
apps/backend/scripts/build_sidecar.py, package.json (build script)
```

---

### Task 1: Scaffold the frontend and tooling

**Files:** Create `apps/desktop/{package.json,tsconfig.json,vite.config.ts,index.html,src/main.tsx,src/App.tsx,src/styles.css,src/__tests__/smoke.test.tsx}`; modify root `.gitignore`.

**Interfaces:** Produces `apps/desktop` workspace package named `desktop` with scripts `dev` (vite), `build` (`tsc --noEmit && vite build`), `test` (`vitest run`), `tauri` (`tauri`), `check-types`.

- [ ] **Step 1:** Write `smoke.test.tsx`: renders `<App />` and expects the heading "Music Transpose".
- [ ] **Step 2:** Create the package files with dependencies at the versions in the survey (react 19, vite, vitest, jsdom, Testing Library, `@tauri-apps/api`, plugins, `@tauri-apps/cli`). Run `pnpm install` from the repo root. Run `pnpm --filter desktop test`. Expected: FAIL (no heading).
- [ ] **Step 3:** Implement the placeholder `App` with the heading. Run test. Expected: PASS. Run `pnpm --filter desktop build`. Expected: success.
- [ ] **Step 4:** Commit.

---

### Task 2: Protocol types and the `Backend` client

**Files:** Create `src/backend/protocol.ts`, `src/backend/Backend.ts`, `src/__tests__/Backend.test.ts`.

**Interfaces:**
- `protocol.ts`: `Finding {check: string; severity: "error" | "warning"; measure: string | null; message: string}`; `Interval {name: string; register: "same" | "shifted"; outOfRange: number}`; `PipelineParams {pdf: string; source: "alto" | "tenor"; register?: "auto" | "same" | "shifted"; force?: boolean; outDir?: string; audiveris?: string; musescore?: string}`; `PipelineResult {originalMusicxml: string; tenorMusicxml: string; pdf: string; interval: Interval; findings: Finding[]; warnings: string[]}`; `DoctorResult {audiveris: string | null; musescore: string | null}`; `ProgressEvent {stage: string; pct: number}`; `class BackendError extends Error {code: string; details?: {findings?: Finding[]}}`.
- `Backend.ts`: `interface Transport { write(line: string): Promise<void>; onLine(cb: (line: string) => void): void; onClose(cb: () => void): void; close(): Promise<void> }`; `class Backend { constructor(transport: Transport); ready(): Promise<void>; call<T>(cmd: string, params?: object, onProgress?: (e: ProgressEvent) => void): PendingCall<T>; cancel(id: number): void; close(): Promise<void>; onClose(cb: () => void): void }` with `PendingCall<T> = { id: number; result: Promise<T> }`.

- [ ] **Step 1: Write failing tests** with a fake transport: `ready resolves on the ready message and call waits for it`, `call writes one JSON line with increasing ids`, `result resolves the matching call only`, `progress events reach onProgress for that id`, `error message rejects with BackendError carrying code and details`, `lines split across chunks and several per chunk are reassembled`, `non-JSON line is ignored`, `closing the transport rejects pending calls and ready`, `cancel sends the cancel command with the target id`, `calls made after close reject immediately`.
- [ ] **Step 2: Run.** Expected: FAIL. **Step 3: Implement. Step 4: Run.** Expected: PASS. **Step 5: Commit.**

---

### Task 3: Tauri transport and mock transport

**Files:** Create `src/backend/tauriTransport.ts`, `src/backend/mockTransport.ts`, `src/__tests__/tauriTransport.test.ts`.

**Interfaces:** `createTauriTransport(): Promise<Transport>` — `Command.sidecar("binaries/backend", ["serve"])` from `@tauri-apps/plugin-shell`, `spawn()`, stdout `data` → `onLine` per line (handles chunks), `close` event → `onClose`, `write` appends `"\n"`, `close()` kills the child. `createMockTransport(script?: MockScript): Transport` — in-memory fake sidecar answering `doctor` and `pipeline` with scripted progress and results (used by tests, dev preview via `?mock`, and Playwright screenshots).

- [ ] **Step 1: Write failing tests** with `vi.mock("@tauri-apps/plugin-shell")`: `spawns the sidecar with the serve argument`, `stdout chunks are delivered as lines`, `write appends a newline`, `close event notifies listeners`, `close kills the child`; and for the mock: `answers doctor` and `plays progress then result for pipeline`.
- [ ] **Step 2: Run.** Expected: FAIL. **Step 3: Implement. Step 4: Run.** Expected: PASS. **Step 5: Commit.**

---

### Task 4: State, settings and pure helpers

**Files:** Create `src/state/jobReducer.ts`, `src/state/settings.ts`, `src/lib/describeInterval.ts`, `src/lib/fileName.ts` and tests.

**Interfaces:**
- `JobState = {phase: "idle"} | {phase: "running"; stage: string; pct: number; jobId: number} | {phase: "done"; result: PipelineResult} | {phase: "failed"; code: string; message: string; findings: Finding[]}`; `JobAction` = `start`, `progress`, `finished`, `failed`, `reset`; `jobReducer(state, action): JobState` — `start` ignored while running (double-click guard); `progress` for a stale `jobId` ignored.
- `describeInterval(name: string, register: "same" | "shifted"): string` → e.g. `"Up a perfect 4th (same sounding pitch)"`, `"Down a perfect 5th (sounds an octave lower)"`, `"Down a perfect 4th (same sounding pitch)"`, `"Up a perfect 5th (sounds an octave higher)"`.
- `baseName(path: string): string` (handles `/` and `\`), `isPdf(path: string): boolean` (case-insensitive).
- `loadSettings(storage: Pick<Storage, "getItem">): Settings`, `saveSettings(storage, settings)`; `Settings {source: "alto" | "tenor"; register: "auto" | "same" | "shifted"; audiveris?: string; musescore?: string; outDir?: string}`; corrupt or missing JSON → defaults (`alto`, `auto`).

- [ ] **Step 1: Write failing tests** for each unit (reducer transitions incl. double start and stale progress; the four interval sentences; Windows and Unix paths with Hebrew names; `isPdf`; settings round trip and corrupt data).
- [ ] **Step 2: Run.** Expected: FAIL. **Step 3: Implement. Step 4: Run.** Expected: PASS. **Step 5: Commit.**

---

### Task 5: Backend hook and the UI

**Files:** Create `src/state/useBackend.ts`, `src/components/{ToolStatus,FilePicker,ModePicker,ProgressView,FindingsList,ResultCard,ErrorBanner}.tsx`, rewrite `App.tsx` and `styles.css`, tests in `src/__tests__/App.test.tsx`.

**Interfaces:**
- `useBackend(createTransport: () => Promise<Transport>): {status: "starting" | "ready" | "stopped"; backend: Backend | null; restart(): void}`.
- `App` props: `{createTransport?: () => Promise<Transport>; pickPdf?: () => Promise<string | null>; pickExecutable?: (label: string) => Promise<string | null>; pickFolder?: () => Promise<string | null>; openPath?: (path: string) => Promise<void>; revealPath?: (path: string) => Promise<void>}` — all default to the Tauri implementations so tests inject fakes.
- Behaviour: tool status chips from `doctor` with "Locate…" for a missing tool (saved to settings, re-runs doctor); Convert disabled until a PDF is chosen and the backend is ready; progress view with stage names (`omr` → "Reading the sheet", `validate` → "Checking the result", `transpose` → "Transposing", `render` → "Engraving the PDF"); Cancel; failure `validation_failed` lists findings with **Convert anyway**; `tool_not_found` shows an error banner naming the tool; `cancelled` returns to idle quietly; success card shows `describeInterval`, warnings, finding counts, **Open PDF**, **Show in folder**, **Convert another**; a stopped backend shows a banner with **Restart**.

- [ ] **Step 1: Write failing tests** (Testing Library, mock transport with scripts): `starts in a starting state then shows ready`, `convert is disabled until a pdf is chosen`, `running a job shows stage labels and then the result card`, `non-pdf choice shows an error and does not start`, `validation failure lists findings and convert anyway resends with force`, `missing tool shows a banner and Locate saves the path`, `cancel returns to idle`, `double click starts one job`, `backend stopping shows restart and restart recovers`, `settings restore the last mode`.
- [ ] **Step 2: Run.** Expected: FAIL. **Step 3: Implement.** **Step 4: Run all desktop tests.** Expected: PASS. **Step 5: Commit.**

---

### Task 6: Visual review of the UI (throwaway servers)

**Files:** Modify `src/main.tsx` (use the mock transport when the URL has `?mock`, DEV builds only); scripts in the scratchpad.

- [ ] **Step 1:** Start a throwaway Vite dev server, drive it with Playwright's cached Chromium at 880×640 and a narrow width, in light and dark, through: idle, running, success, validation failure, tool missing, backend stopped. Save screenshots to the scratchpad and read them.
- [ ] **Step 2:** Fix any visual problems found (alignment, contrast, truncation, Hebrew file name display). Stop the server.
- [ ] **Step 3:** Run all desktop tests and the production build. Commit.

---

### Task 7: Tauri shell

**Files:** Create `src-tauri/{Cargo.toml,build.rs,tauri.conf.json,capabilities/default.json,src/main.rs,src/lib.rs,icons/*}`; modify `.gitignore` (`src-tauri/target`, `src-tauri/binaries`, `src-tauri/gen`).

**Interfaces:** `tauri.conf.json`: productName `Music Transpose`, identifier `com.tsemach.doron-desktop`, one 880×640 window titled Music Transpose, `build.devUrl` `http://localhost:1420`, `frontendDist` `../dist`, `bundle.externalBin: ["binaries/backend"]`. `capabilities/default.json`: `core:default`, `dialog:default`, `opener:default` plus `opener:allow-open-path` and `opener:allow-reveal-item-in-dir` for any path, and the sidecar spawn permission from Global Constraints. Rust exposes one command `ui_log(message: String)` printing to stderr (diagnostics for headless smoke tests).

- [ ] **Step 1:** Generate icons from a simple source image. Write the Rust files and config.
- [ ] **Step 2:** Create a placeholder sidecar binary named with the host target triple (`rustc -vV`) so the build can start. Run `cargo check` in `src-tauri`. Expected: success (first run downloads crates; run in the background).
- [ ] **Step 3:** Commit.

---

### Task 8: Freeze the sidecar

**Files:** Create `apps/backend/scripts/build_sidecar.py`; modify `apps/backend/pyproject.toml` (dev dependency `pyinstaller`), `apps/backend/package.json` (`build` script), `apps/desktop/package.json` (dev dependency `"backend": "workspace:*"`), `turbo.json` (outputs for the backend build).

**Interfaces:** `build_sidecar.py` runs `pyinstaller --onefile --name backend` on a tiny entry script that calls `backend.cli.main`, with `--collect-data music21` and whatever hidden imports the first run shows are needed, then copies the result to `apps/desktop/src-tauri/binaries/backend-<triple>[.exe]` (triple from `rustc -vV`).

- [ ] **Step 1:** Add the dev dependency and the script; run it. Fix missing-module / data-file errors until the binary starts.
- [ ] **Step 2:** Verify with a throwaway script: spawn the frozen binary with `serve`, expect `ready`, send `doctor` and expect a result. Record binary size and startup time in the ledger.
- [ ] **Step 3:** Commit (the binary itself stays git-ignored).

---

### Task 9: Build the app and smoke-test it

**Files:** Modify `src/main.tsx` to call `ui_log` on state changes.

- [ ] **Step 1:** Run `pnpm --filter desktop tauri build --debug --no-bundle` (compiles Rust, bundles the frontend). Expected: a runnable binary under `src-tauri/target/debug`.
- [ ] **Step 2:** Launch it headless (`xvfb-run`, or WSLg `DISPLAY=:0`) with a timeout and capture stderr. Expected: a `backend ready` line from `ui_log`, proving the webview loaded, the sidecar was spawned through the shell plugin and answered `ready` and `doctor`. Record what happens if it fails and fix.
- [ ] **Step 3:** Try a full run through the real app if a way to drive it exists (an `ASCURIX_AUTORUN=<pdf>` environment variable read by the frontend is acceptable for the smoke test and may be removed afterwards); otherwise rely on the Task 8 and Phase 5a integration tests for the pipeline itself.
- [ ] **Step 4:** Commit.

---

## Self-review

- **Spec coverage:** Phase 5 asks for upload, operation picker, progress, validation flags, download (Tasks 4–5; "download" is "Open PDF / Show in folder" because outputs are written next to the PDF or to a chosen folder), sidecar per CLAUDE.md (Tasks 2, 3, 7, 8), Turbo wiring (Task 8). Verovio preview from CLAUDE.md is **not** included: the PDF viewer opens the engraved result and the review step is the findings list. Called out as a known gap.
- **Type consistency:** `Transport`, `Backend`, `PipelineParams`/`PipelineResult` match the sidecar's camelCase results from Phase 5a; `JobState` is the only UI state shape.
- **Review Focus:** Backend tests cover chunking, junk lines, close-while-pending; App tests cover double start, cancel, stopped backend, validation retry; Hebrew names covered by `baseName` and the Task 6 screenshots.
- **My calls:** no Verovio; folder-based "download"; settings in `localStorage`; mock transport kept in the production bundle behind the `?mock` DEV-only branch; autorun env var only for the smoke test.
