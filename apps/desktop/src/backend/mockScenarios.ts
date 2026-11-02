import type { Transport } from "./Backend";
import { createMockTransport, SAMPLE_RESULT, type MockScript } from "./mockTransport";

const SCENARIOS: Record<string, MockScript> = {
  ok: { stepMs: 400 },
  slow: { stepMs: 2000 },
  tools: { stepMs: 400, doctor: { audiveris: null, musescore: "/mock/MuseScore" } },
  crash: { stepMs: 400, outcome: () => ({ type: "crash" }) },
  validation: {
    stepMs: 400,
    outcome: () => ({
      type: "error",
      code: "validation_failed",
      message: "invalid",
      details: {
        findings: [
          { check: "empty-measure", severity: "error", measure: "34", message: "measure has no notes or rests" },
          { check: "key-signature-flip", severity: "warning", measure: "66", message: "key signature changes at bar 66 and returns at bar 72" },
        ],
      },
    }),
  },
  forced: {
    stepMs: 400,
    outcome: () => ({
      type: "result",
      result: {
        ...SAMPLE_RESULT,
        interval: { name: "-P5", register: "shifted", outOfRange: 3 },
        findings: [{ check: "empty-measure", severity: "error", measure: "34", message: "measure has no notes or rests" }],
        warnings: ["Part is declared as a tenor saxophone (name or transposition) but --from alto was given"],
      },
    }),
  },
};

export function mockTransportFor(scenario: string): () => Promise<Transport> {
  const script = SCENARIOS[scenario] ?? SCENARIOS.ok!;
  return async () => createMockTransport(script);
}
