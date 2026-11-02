import type { Finding, PipelineResult } from "../backend/protocol";

export type JobState =
  | { phase: "idle" }
  | { phase: "running"; jobId: number; stage: string; pct: number }
  | { phase: "done"; result: PipelineResult }
  | { phase: "failed"; code: string; message: string; findings: Finding[] };

export type JobAction =
  | { type: "start"; jobId: number }
  | { type: "progress"; jobId: number; stage: string; pct: number }
  | { type: "finished"; jobId: number; result: PipelineResult }
  | { type: "failed"; jobId: number; code: string; message: string; findings: Finding[] }
  | { type: "reset" };

export function jobReducer(state: JobState, action: JobAction): JobState {
  switch (action.type) {
    case "start":
      return state.phase === "running" ? state : { phase: "running", jobId: action.jobId, stage: "starting", pct: 0 };
    case "progress":
      return isCurrent(state, action.jobId) ? { ...state, stage: action.stage, pct: action.pct } : state;
    case "finished":
      return isCurrent(state, action.jobId) ? { phase: "done", result: action.result } : state;
    case "failed":
      return isCurrent(state, action.jobId)
        ? { phase: "failed", code: action.code, message: action.message, findings: action.findings }
        : state;
    case "reset":
      return { phase: "idle" };
  }
}

function isCurrent(state: JobState, jobId: number): state is Extract<JobState, { phase: "running" }> {
  return state.phase === "running" && state.jobId === jobId;
}
