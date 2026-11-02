# Phase 5a: Python Sidecar Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `python -m backend serve` runs a long-lived process that the desktop app talks to over newline-delimited JSON, exactly as CLAUDE.md specifies.

**Architecture:** `backend/sidecar/` with `protocol` (message shapes and a locked writer), `handlers` (commands mapping to the existing functions, with error classification), and `server` (read loop, a thread per request, cancel registry). The `serve` CLI command wires real stdin/stdout with the stdout-hygiene rules.

**Tech Stack:** Python 3 stdlib (`json`, `threading`), existing backend functions, pytest.

**Spec:** `CLAUDE.md` "Sidecar protocol" section; `docs/superpowers/specs/2026-11-02-pdf-to-musicxml-design.md` (Phase 5).

## Global Constraints (from CLAUDE.md, copied)

- Newline-delimited JSON over stdin/stdout. stdout carries protocol messages **only**; stderr is logs only.
- `{"type":"ready","version":"0.1"}` once at startup before anything else.
- Every request has an `id`; every reply echoes it. Replies per request: zero or more `{"id","type":"progress","stage","pct"}`, then exactly one `{"id","type":"result",...}` or `{"id","type":"error","message"}`.
- Pass file paths, never contents.
- Keep the real stdout for protocol and set `sys.stdout = sys.stderr`; flush after every message; guard writes with a lock.
- Force UTF-8 on stdin/stdout (`reconfigure(encoding="utf-8")`, `ensure_ascii=False`): Hebrew file names on Windows.
- Each request in its own thread so the read loop stays free; a `cancel` command kills the running Audiveris/MuseScore subprocess.
- Lifecycle: stdin closing ends the process; running work is cancelled.
- Result keys are camelCase (consumed by TypeScript).

## Review Focus

- Malformed JSON, a non-object line, a missing `id` or `cmd`, an unknown command: each gets an `error` reply (id echoed when present) and the loop keeps running.
- A stray `print()` inside a handler never reaches the protocol stream.
- Two requests in flight at once get independent replies with the right ids; cancel of one leaves the other running; cancelling an unknown id replies `cancelled: false`.
- A handler that raises an unexpected exception produces an `error` reply, not a dead loop or a missing reply.
- stdin EOF cancels running work and the process exits promptly.
- Hebrew in paths and messages survives a round trip.

## File Structure

- `backend/sidecar/__init__.py`, `protocol.py`, `handlers.py`, `server.py`
- `backend/cli.py` — modify: `serve` command
- `tests/sidecar/` — tests per module plus a subprocess integration test

---

### Task 1: Protocol messages and locked writer

**Files:** Create `sidecar/__init__.py`, `sidecar/protocol.py`, `tests/sidecar/test_protocol.py`

**Interfaces:**
- Produces: `PROTOCOL_VERSION = "0.1"`; `def ready() -> dict`; `def progress(request_id: int, stage: str, pct: int) -> dict`; `def result(request_id: int, data: dict) -> dict` (merges `data` into `{"id", "type": "result"}`); `def error(request_id: int | None, message: str, code: str = "failed", details: dict | None = None) -> dict` (`details` merged under key `"details"` only when given); `class MessageWriter: def __init__(self, stream: TextIO); def send(self, message: dict) -> None` — one `json.dumps(..., ensure_ascii=False)` line, newline, flush, all under a `threading.Lock`.

- [ ] **Step 1: Write failing tests:** `test_message_shapes_match_protocol`, `test_error_includes_details_only_when_given`, `test_writer_emits_one_utf8_line_per_message` (Hebrew text unescaped), `test_concurrent_senders_never_interleave_lines` (8 threads × 50 messages, every line parses).
- [ ] **Step 2: Run** `apps/backend/.venv/bin/pytest apps/backend/tests/sidecar/test_protocol.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.** **Step 4: Run again.** Expected: PASS. **Step 5: Commit.**

---

### Task 2: Handlers and error classification

**Files:** Create `sidecar/handlers.py`, `tests/sidecar/test_handlers.py`

**Interfaces:**
- Consumes: `run_pipeline`, `validate_musicxml`, `find_audiveris`, `find_musescore`, all `BackendError` subclasses.
- Produces:
  - `@dataclass class RequestContext: progress: Callable[[str, int], None]; cancel: threading.Event`
  - `Handler = Callable[[dict, RequestContext], dict]`
  - `HANDLERS: dict[str, Handler]` with `doctor`, `validate`, `pipeline`.
  - `doctor(params, ctx) -> {"audiveris": str | None, "musescore": str | None}`: each tool resolved with an optional `audiveris` / `musescore` path override in `params`; a missing tool gives `None`, never an error.
  - `validate(params, ctx) -> {"findings": [finding dicts]}` from `params["musicxml"]`.
  - `pipeline(params, ctx) -> {"originalMusicxml", "tenorMusicxml", "pdf", "interval": {"name", "register", "outOfRange"}, "findings": [...], "warnings": [...]}` from `params`: `pdf`, `source`, optional `register` (default `auto`), `force` (default false), `outDir` (default folder beside the PDF named after its stem), `audiveris`, `musescore`. Progress is forwarded through `ctx.progress`.
  - `def classify(error: Exception) -> tuple[str, str, dict | None]` returning `(code, message, details)`: `ValidationFailedError` → `"validation_failed"` with `{"findings": [...]}`; `CancelledError` → `"cancelled"`; `ExecutableNotFoundError` → `"tool_not_found"`; `InvalidInputError` → `"invalid_input"`; other `BackendError` → `"failed"`; anything else → `"internal"` with the exception text.
  - Finding dict shape: `{"check", "severity", "measure", "message"}`.

- [ ] **Step 1: Write failing tests** with the backend functions monkeypatched: `test_doctor_reports_found_and_missing_tools`, `test_doctor_passes_overrides`, `test_validate_returns_findings_as_dicts`, `test_pipeline_maps_params_and_returns_camel_case_result`, `test_pipeline_defaults_out_dir_beside_pdf`, `test_pipeline_forwards_progress`, and one test per row of `classify` (six).
- [ ] **Step 2: Run them.** Expected: FAIL. **Step 3: Implement.** **Step 4: Run.** Expected: PASS. **Step 5: Commit.**

---

### Task 3: Server loop

**Files:** Create `sidecar/server.py`, `tests/sidecar/test_server.py`

**Interfaces:**
- Consumes: `MessageWriter`, `ready`, `progress`, `result`, `error`, `HANDLERS`, `RequestContext`, `classify`.
- Produces: `def serve(stdin: Iterable[str], writer: MessageWriter, handlers: dict[str, Handler] = HANDLERS) -> None`. Sends `ready` first; for each non-blank line: parse; validate shape; `cancel` is built in (`{"cmd":"cancel","target":<id>}` replies `result {"cancelled": bool}` and sets the target's event); other commands run in a new thread that sends progress and exactly one result or error. On loop end (EOF): set every running request's cancel event and join threads (max 10 s total).

- [ ] **Step 1: Write failing tests** using `io.StringIO` and fake handlers: `test_ready_is_first_message`, `test_result_echoes_id`, `test_progress_then_result`, `test_malformed_json_replies_error_and_continues`, `test_missing_id_or_cmd_replies_error`, `test_unknown_command_replies_error_with_id`, `test_handler_exception_becomes_error_reply`, `test_concurrent_requests_get_independent_replies`, `test_cancel_stops_target_only`, `test_cancel_unknown_id_replies_false`, `test_eof_cancels_running_work`, `test_hebrew_params_round_trip`.
- [ ] **Step 2: Run them.** Expected: FAIL. **Step 3: Implement.** **Step 4: Run.** Expected: PASS. **Step 5: Commit.**

---

### Task 4: `serve` command, stdout hygiene and subprocess integration

**Files:** Modify `cli.py`, `tests/test_cli.py`; create `tests/sidecar/test_serve_process.py`

**Interfaces:**
- Produces: CLI `serve`; `def run_server(stdin: TextIO, stdout: TextIO) -> int` in `cli.py` (or `sidecar/__init__.py`) that reconfigures both streams to UTF-8, keeps `stdout` for the writer, sets `sys.stdout = sys.stderr` for the duration, calls `serve`, returns 0.

- [ ] **Step 1: Write failing tests:** `test_stray_print_does_not_reach_protocol_stream` (handler prints; protocol stream contains only JSON lines); integration (skipped without Audiveris and MuseScore): spawn `python -m backend serve` as a real subprocess and check `test_ready_then_doctor`, `test_unknown_command_error_keeps_process_alive`, `test_pipeline_on_hebrew_named_copy_of_funk_out` (progress messages then result with an existing PDF), `test_cancel_kills_running_pipeline_quickly` (start pipeline, cancel after ~1 s, expect error code `cancelled` within 10 s), `test_closing_stdin_exits_process`.
- [ ] **Step 2: Run them.** Expected: FAIL. **Step 3: Implement.** **Step 4: Run the full suite.** Expected: PASS. **Step 5: Commit.**

---

## Self-review

- **Spec coverage:** every CLAUDE.md protocol rule appears under Global Constraints and is exercised by a named test (ready, ids, progress/result/error, stdout hygiene, UTF-8, threads + cancel, EOF lifecycle).
- **Beyond CLAUDE.md:** `doctor` command (the UI needs tool status), structured error `code` and `details` (UI shows validation findings and offers "convert anyway"), camelCase results.
- **Type consistency:** `RequestContext` is the only handler context type; `classify` is the single place errors map to codes.
- **Review Focus:** each line has a named test in Tasks 3–4.
- **My calls:** command set limited to `doctor`, `validate`, `pipeline`, `cancel` for the GUI's needs; progress percentages come from the pipeline unchanged.
