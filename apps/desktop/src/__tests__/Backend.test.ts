import { Backend } from "../backend/Backend";
import { BackendError } from "../backend/protocol";
import { FakeTransport } from "./fakeTransport";

const READY = { type: "ready", version: "0.1" };

function setup(emitReady = true) {
  const transport = new FakeTransport();
  const backend = new Backend(transport);
  if (emitReady) transport.emitMessage(READY);
  return { transport, backend };
}

test("ready resolves on the ready message and calls wait for it", async () => {
  const { transport, backend } = setup(false);
  const call = backend.call("doctor");

  await new Promise((resolve) => setTimeout(resolve, 10));
  expect(transport.written).toHaveLength(0);

  transport.emitMessage(READY);
  await backend.ready();
  await vi.waitFor(() => expect(transport.written).toHaveLength(1));
  transport.emitMessage({ id: call.id, type: "result", audiveris: null, musescore: null });
  await expect(call.result).resolves.toEqual({ audiveris: null, musescore: null });
});

test("call writes one JSON line per request with increasing ids", async () => {
  const { transport, backend } = setup();

  const first = backend.call("doctor");
  const second = backend.call("validate", { musicxml: "a.musicxml" });
  await vi.waitFor(() => expect(transport.written).toHaveLength(2));

  expect(transport.written.every((line) => line.endsWith("\n") && line.split("\n").length === 2)).toBe(true);
  expect(second.id).toBeGreaterThan(first.id);
  expect(transport.requests()[1]).toEqual({ id: second.id, cmd: "validate", params: { musicxml: "a.musicxml" } });
});

test("a result resolves only the matching call", async () => {
  const { transport, backend } = setup();
  const first = backend.call<{ n: number }>("a");
  const second = backend.call<{ n: number }>("b");
  await vi.waitFor(() => expect(transport.written).toHaveLength(2));

  transport.emitMessage({ id: second.id, type: "result", n: 2 });

  await expect(second.result).resolves.toEqual({ n: 2 });
  let firstSettled = false;
  first.result.then(() => (firstSettled = true));
  await new Promise((resolve) => setTimeout(resolve, 10));
  expect(firstSettled).toBe(false);
});

test("progress events reach onProgress for that call", async () => {
  const { transport, backend } = setup();
  const seen: Array<{ stage: string; pct: number }> = [];
  const call = backend.call("pipeline", {}, (event) => seen.push(event));
  await vi.waitFor(() => expect(transport.written).toHaveLength(1));

  transport.emitMessage({ id: call.id, type: "progress", stage: "omr", pct: 5 });
  transport.emitMessage({ id: call.id + 100, type: "progress", stage: "other", pct: 9 });
  transport.emitMessage({ id: call.id, type: "result" });
  await call.result;

  expect(seen).toEqual([{ stage: "omr", pct: 5 }]);
});

test("an error message rejects with a BackendError carrying code and details", async () => {
  const { transport, backend } = setup();
  const call = backend.call("pipeline");
  await vi.waitFor(() => expect(transport.written).toHaveLength(1));
  const findings = [{ check: "empty-measure", severity: "error", measure: "34", message: "no notes" }];

  transport.emitMessage({ id: call.id, type: "error", message: "bad", code: "validation_failed", details: { findings } });

  const failure = await call.result.catch((error: unknown) => error);
  expect(failure).toBeInstanceOf(BackendError);
  expect(failure).toMatchObject({ message: "bad", code: "validation_failed", details: { findings } });
});

test("lines split across chunks and several per chunk are reassembled", async () => {
  const { transport, backend } = setup();
  const first = backend.call<{ v: number }>("a");
  const second = backend.call<{ v: number }>("b");
  await vi.waitFor(() => expect(transport.written).toHaveLength(2));
  const one = JSON.stringify({ id: first.id, type: "result", v: 1 });
  const two = JSON.stringify({ id: second.id, type: "result", v: 2 });

  transport.emitChunk(one.slice(0, 10));
  transport.emitChunk(`${one.slice(10)}\n${two}`);
  transport.emitChunk("\n");

  await expect(first.result).resolves.toEqual({ v: 1 });
  await expect(second.result).resolves.toEqual({ v: 2 });
});

test("a non-JSON line is ignored", async () => {
  const { transport, backend } = setup();
  const call = backend.call<{ ok: boolean }>("a");
  await vi.waitFor(() => expect(transport.written).toHaveLength(1));

  transport.emitChunk("some stray library output\n");
  transport.emitMessage({ id: call.id, type: "result", ok: true });

  await expect(call.result).resolves.toEqual({ ok: true });
});

test("closing the transport rejects pending calls and ready", async () => {
  const { transport, backend } = setup(false);
  const early = backend.ready();
  const caught = early.catch((error: unknown) => error);

  transport.emitClose();

  expect(await caught).toMatchObject({ code: "backend_stopped" });

  const second = setup();
  const pending = second.backend.call("a");
  await vi.waitFor(() => expect(second.transport.written).toHaveLength(1));
  second.transport.emitClose();
  await expect(pending.result).rejects.toMatchObject({ code: "backend_stopped" });
});

test("cancel sends the cancel command with the target id", async () => {
  const { transport, backend } = setup();
  const call = backend.call("pipeline");
  await vi.waitFor(() => expect(transport.written).toHaveLength(1));

  backend.cancel(call.id);

  await vi.waitFor(() => expect(transport.written).toHaveLength(2));
  expect(transport.requests()[1]).toMatchObject({ cmd: "cancel", params: { target: call.id } });
});

test("calls made after close reject immediately", async () => {
  const { transport, backend } = setup();
  transport.emitClose();

  await expect(backend.call("doctor").result).rejects.toMatchObject({ code: "backend_stopped" });
});
