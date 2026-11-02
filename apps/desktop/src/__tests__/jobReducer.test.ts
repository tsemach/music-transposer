import type { PipelineResult } from "../backend/protocol";
import { jobReducer, type JobState } from "../state/jobReducer";

const RESULT = { pdf: "/a.pdf" } as PipelineResult;
const RUNNING: JobState = { phase: "running", jobId: 1, stage: "omr", pct: 5 };

test("start moves idle to running", () => {
  expect(jobReducer({ phase: "idle" }, { type: "start", jobId: 1 })).toEqual({
    phase: "running",
    jobId: 1,
    stage: "starting",
    pct: 0,
  });
});

test("start while running is ignored so a double click cannot start two jobs", () => {
  expect(jobReducer(RUNNING, { type: "start", jobId: 2 })).toBe(RUNNING);
});

test("start works again after a result or a failure", () => {
  const done: JobState = { phase: "done", result: RESULT };
  const failed: JobState = { phase: "failed", code: "failed", message: "x", findings: [] };

  expect(jobReducer(done, { type: "start", jobId: 3 }).phase).toBe("running");
  expect(jobReducer(failed, { type: "start", jobId: 4 }).phase).toBe("running");
});

test("progress updates the matching job and ignores stale ones", () => {
  expect(jobReducer(RUNNING, { type: "progress", jobId: 1, stage: "render", pct: 80 })).toMatchObject({
    stage: "render",
    pct: 80,
  });
  expect(jobReducer(RUNNING, { type: "progress", jobId: 9, stage: "render", pct: 80 })).toBe(RUNNING);
});

test("finished and failed apply to the current job only", () => {
  expect(jobReducer(RUNNING, { type: "finished", jobId: 1, result: RESULT })).toEqual({ phase: "done", result: RESULT });
  expect(jobReducer(RUNNING, { type: "finished", jobId: 2, result: RESULT })).toBe(RUNNING);
  expect(jobReducer(RUNNING, { type: "failed", jobId: 1, code: "validation_failed", message: "m", findings: [] })).toEqual({
    phase: "failed",
    code: "validation_failed",
    message: "m",
    findings: [],
  });
  expect(jobReducer(RUNNING, { type: "failed", jobId: 2, code: "x", message: "m", findings: [] })).toBe(RUNNING);
});

test("reset returns to idle from anywhere", () => {
  expect(jobReducer(RUNNING, { type: "reset" })).toEqual({ phase: "idle" });
  expect(jobReducer({ phase: "done", result: RESULT }, { type: "reset" })).toEqual({ phase: "idle" });
});
