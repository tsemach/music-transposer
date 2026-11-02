import { Command } from "@tauri-apps/plugin-shell";

import type { Transport } from "./Backend";

export async function createTauriTransport(): Promise<Transport> {
  const command = Command.sidecar("binaries/backend", ["serve"]);
  const earlyChunks: string[] = [];
  const closeListeners: Array<() => void> = [];
  let dataListener: ((chunk: string) => void) | null = null;
  let closed = false;

  const notifyClosed = () => {
    closed = true;
    closeListeners.forEach((listener) => listener());
  };

  command.stdout.on("data", (line: string) => {
    const chunk = `${line}\n`;
    if (dataListener) dataListener(chunk);
    else earlyChunks.push(chunk);
  });
  command.stderr.on("data", (line: string) => console.debug("[backend]", line));
  command.on("close", notifyClosed);
  command.on("error", (message: string) => {
    console.error("[backend] failed to run", message);
    notifyClosed();
  });

  const child = await command.spawn();

  return {
    write: (data) => child.write(data),
    onData(listener) {
      dataListener = listener;
      earlyChunks.splice(0).forEach(listener);
    },
    onClose(listener) {
      closeListeners.push(listener);
      if (closed) listener();
    },
    close: () => child.kill(),
  };
}
