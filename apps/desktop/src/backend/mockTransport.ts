import type { Transport } from "./Backend";
import type { DoctorResult, ErrorDetails, PipelineParams, PipelineResult } from "./protocol";

export type MockOutcome =
  | { type: "result"; result: PipelineResult }
  | { type: "error"; code: string; message: string; details?: ErrorDetails }
  | { type: "crash" };

export interface MockScript {
  doctor?: DoctorResult;
  stepMs?: number;
  outcome?: (params: PipelineParams) => MockOutcome;
}

export const SAMPLE_RESULT: PipelineResult = {
  originalMusicxml: "/music/Gymnopedie.musicxml",
  tenorMusicxml: "/music/Gymnopedie.tenor.musicxml",
  pdf: "/music/Gymnopedie.tenor.pdf",
  interval: { name: "P4", register: "same", outOfRange: 0 },
  findings: [
    { check: "key-signature-flip", severity: "warning", measure: "66", message: "key signature changes at bar 66 and returns at bar 72" },
  ],
  warnings: [],
};

const STAGES: Array<[string, number]> = [
  ["omr", 5],
  ["validate", 55],
  ["transpose", 65],
  ["render", 80],
  ["done", 100],
];

const DEFAULT_DOCTOR: DoctorResult = { audiveris: "/mock/Audiveris", musescore: "/mock/MuseScore" };

interface Request {
  id: number;
  cmd: string;
  params?: Record<string, unknown>;
}

export function createMockTransport(script: MockScript = {}): Transport {
  const stepMs = script.stepMs ?? 0;
  const closeListeners: Array<() => void> = [];
  const cancelled = new Set<number>();
  const running = new Set<number>();
  const earlyChunks: string[] = [];
  let dataListener: ((chunk: string) => void) | null = null;
  let closed = false;

  const emit = (message: object) => {
    if (closed) return;
    const chunk = `${JSON.stringify(message)}\n`;
    if (dataListener) dataListener(chunk);
    else earlyChunks.push(chunk);
  };
  const emitClose = () => {
    closed = true;
    closeListeners.forEach((listener) => listener());
  };
  const pause = () => new Promise((resolve) => setTimeout(resolve, stepMs));

  async function runPipeline(id: number, params: PipelineParams): Promise<void> {
    const outcome = script.outcome?.(params) ?? { type: "result", result: SAMPLE_RESULT };
    const stages = outcome.type === "result" ? STAGES : STAGES.slice(0, outcome.type === "crash" ? 1 : 2);
    running.add(id);
    for (const [stage, pct] of stages) {
      await pause();
      if (cancelled.has(id)) {
        running.delete(id);
        emit({ id, type: "error", message: "Cancelled", code: "cancelled" });
        return;
      }
      emit({ id, type: "progress", stage, pct });
    }
    running.delete(id);
    if (outcome.type === "crash") emitClose();
    else if (outcome.type === "error") emit({ id, type: "error", message: outcome.message, code: outcome.code, details: outcome.details });
    else emit({ id, type: "result", ...outcome.result });
  }

  setTimeout(() => emit({ type: "ready", version: "0.1" }), 0);

  return {
    async write(data) {
      const request = JSON.parse(data) as Request;
      if (request.cmd === "doctor") emit({ id: request.id, type: "result", ...(script.doctor ?? DEFAULT_DOCTOR) });
      else if (request.cmd === "pipeline") void runPipeline(request.id, request.params as unknown as PipelineParams);
      else if (request.cmd === "cancel") {
        const target = Number(request.params?.target);
        const wasRunning = running.has(target);
        cancelled.add(target);
        emit({ id: request.id, type: "result", cancelled: wasRunning });
      } else emit({ id: request.id, type: "error", message: `Unknown command: ${request.cmd}`, code: "unknown_command" });
    },
    onData(listener) {
      dataListener = listener;
      earlyChunks.splice(0).forEach(listener);
    },
    onClose: (listener) => void closeListeners.push(listener),
    async close() {
      emitClose();
    },
  };
}
