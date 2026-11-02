import { useCallback, useReducer, useRef } from "react";

import type { Backend } from "../backend/Backend";
import { BackendError, type PipelineParams, type PipelineResult } from "../backend/protocol";
import { jobReducer, type JobAction } from "./jobReducer";

export function useJobRunner(backend: Backend | null) {
  const [job, dispatch] = useReducer(jobReducer, { phase: "idle" });
  const counter = useRef(0);
  const busy = useRef(false);
  const active = useRef<number | null>(null);

  const run = useCallback(
    async (params: PipelineParams) => {
      if (!backend || busy.current) return;
      busy.current = true;
      const jobId = ++counter.current;
      dispatch({ type: "start", jobId });
      const call = backend.call<PipelineResult>("pipeline", params, (event) =>
        dispatch({ type: "progress", jobId, ...event }),
      );
      active.current = call.id;
      try {
        dispatch({ type: "finished", jobId, result: await call.result });
      } catch (failure) {
        dispatch(toFailure(jobId, failure));
      } finally {
        busy.current = false;
        active.current = null;
      }
    },
    [backend],
  );

  const cancel = useCallback(() => {
    if (backend && active.current !== null) backend.cancel(active.current);
  }, [backend]);

  const reset = useCallback(() => dispatch({ type: "reset" }), []);

  return { job, run, cancel, reset };
}

function toFailure(jobId: number, failure: unknown): JobAction {
  if (failure instanceof BackendError) {
    if (failure.code === "cancelled" || failure.code === "backend_stopped") return { type: "reset" };
    return {
      type: "failed",
      jobId,
      code: failure.code,
      message: failure.message,
      findings: failure.details?.findings ?? [],
    };
  }
  return { type: "failed", jobId, code: "internal", message: String(failure), findings: [] };
}
