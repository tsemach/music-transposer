import { createTauriTransport } from "../backend/tauriTransport";

const shell = vi.hoisted(() => {
  type Handler = (payload?: string) => void;
  const state = {
    sidecarArgs: [] as unknown[],
    stdout: new Map<string, Handler>(),
    events: new Map<string, Handler>(),
    written: [] as string[],
    killed: false,
  };
  return state;
});

vi.mock("@tauri-apps/plugin-shell", () => ({
  Command: {
    sidecar: (...args: unknown[]) => {
      shell.sidecarArgs = args;
      return {
        stdout: { on: (event: string, handler: (payload?: string) => void) => shell.stdout.set(event, handler) },
        stderr: { on: () => undefined },
        on: (event: string, handler: (payload?: string) => void) => shell.events.set(event, handler),
        spawn: async () => ({
          write: async (data: string) => void shell.written.push(data),
          kill: async () => void (shell.killed = true),
        }),
      };
    },
  },
}));

beforeEach(() => {
  shell.stdout.clear();
  shell.events.clear();
  shell.written = [];
  shell.killed = false;
});

test("spawns the sidecar with the serve argument", async () => {
  await createTauriTransport();

  expect(shell.sidecarArgs).toEqual(["binaries/backend", ["serve"]]);
});

test("stdout lines are delivered as newline-terminated chunks", async () => {
  const transport = await createTauriTransport();
  const chunks: string[] = [];
  transport.onData((chunk) => chunks.push(chunk));

  shell.stdout.get("data")?.('{"type":"ready"}');

  expect(chunks).toEqual(['{"type":"ready"}\n']);
});

test("data that arrives before a listener is attached is not lost", async () => {
  const transport = await createTauriTransport();
  shell.stdout.get("data")?.('{"type":"ready"}');
  const chunks: string[] = [];

  transport.onData((chunk) => chunks.push(chunk));

  expect(chunks).toEqual(['{"type":"ready"}\n']);
});

test("write passes data through untouched", async () => {
  const transport = await createTauriTransport();

  await transport.write('{"id":1}\n');

  expect(shell.written).toEqual(['{"id":1}\n']);
});

test("the close event notifies listeners", async () => {
  const transport = await createTauriTransport();
  const closed = vi.fn();
  transport.onClose(closed);

  shell.events.get("close")?.();

  expect(closed).toHaveBeenCalledOnce();
});

test("close kills the child", async () => {
  const transport = await createTauriTransport();

  await transport.close();

  expect(shell.killed).toBe(true);
});
