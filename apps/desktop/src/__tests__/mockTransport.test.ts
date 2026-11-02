import { Backend } from "../backend/Backend";
import type { DoctorResult, PipelineResult } from "../backend/protocol";
import { createMockTransport, SAMPLE_RESULT } from "../backend/mockTransport";

test("answers doctor", async () => {
  const backend = new Backend(createMockTransport());

  const reply = await backend.call<DoctorResult>("doctor").result;

  expect(reply.audiveris).toBeTruthy();
  expect(reply.musescore).toBeTruthy();
});

test("plays progress then result for a pipeline run", async () => {
  const backend = new Backend(createMockTransport({ stepMs: 1 }));
  const stages: string[] = [];

  const reply = await backend.call<PipelineResult>("pipeline", { pdf: "/a.pdf", source: "alto" }, (event) =>
    stages.push(event.stage),
  ).result;

  expect(stages).toEqual(["omr", "validate", "transpose", "render", "done"]);
  expect(reply.pdf).toBe(SAMPLE_RESULT.pdf);
});

test("cancel ends the running pipeline with a cancelled error", async () => {
  const backend = new Backend(createMockTransport({ stepMs: 50 }));
  const call = backend.call("pipeline", { pdf: "/a.pdf", source: "alto" });
  await new Promise((resolve) => setTimeout(resolve, 20));

  backend.cancel(call.id);

  await expect(call.result).rejects.toMatchObject({ code: "cancelled" });
});

test("a scripted failure outcome is delivered as an error", async () => {
  const backend = new Backend(
    createMockTransport({
      outcome: () => ({ type: "error", code: "tool_not_found", message: "Audiveris not found" }),
    }),
  );

  await expect(backend.call("pipeline", { pdf: "/a.pdf", source: "alto" }).result).rejects.toMatchObject({
    code: "tool_not_found",
  });
});
