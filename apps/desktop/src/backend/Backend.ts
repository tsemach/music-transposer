import { BackendError, type ErrorDetails, type ProgressEvent } from "./protocol";

export interface Transport {
  write(data: string): Promise<void>;
  onData(listener: (chunk: string) => void): void;
  onClose(listener: () => void): void;
  close(): Promise<void>;
}

export interface PendingCall<T> {
  id: number;
  result: Promise<T>;
}

interface PendingEntry {
  resolve: (value: unknown) => void;
  reject: (error: Error) => void;
  onProgress?: (event: ProgressEvent) => void;
}

type Incoming = Record<string, unknown>;

const stoppedError = () => new BackendError("The backend stopped", "backend_stopped");

export class Backend {
  private nextId = 1;
  private buffer = "";
  private stopped = false;
  private readonly pending = new Map<number, PendingEntry>();
  private readonly closeListeners: Array<() => void> = [];
  private readonly readyPromise: Promise<void>;
  private resolveReady!: () => void;
  private rejectReady!: (error: Error) => void;

  constructor(private readonly transport: Transport) {
    this.readyPromise = new Promise((resolve, reject) => {
      this.resolveReady = resolve;
      this.rejectReady = reject;
    });
    this.readyPromise.catch(() => undefined);
    transport.onData((chunk) => this.handleChunk(chunk));
    transport.onClose(() => this.handleClose());
  }

  ready(): Promise<void> {
    return this.readyPromise;
  }

  call<T>(cmd: string, params: object = {}, onProgress?: (event: ProgressEvent) => void): PendingCall<T> {
    const id = this.nextId++;
    return { id, result: this.send<T>(id, cmd, params, onProgress) };
  }

  cancel(id: number): void {
    void this.call("cancel", { target: id }).result.catch(() => undefined);
  }

  onClose(listener: () => void): void {
    this.closeListeners.push(listener);
  }

  close(): Promise<void> {
    return this.transport.close();
  }

  private async send<T>(
    id: number,
    cmd: string,
    params: object,
    onProgress?: (event: ProgressEvent) => void,
  ): Promise<T> {
    await this.readyPromise;
    if (this.stopped) throw stoppedError();
    return new Promise<T>((resolve, reject) => {
      this.pending.set(id, { resolve: resolve as (value: unknown) => void, reject, onProgress });
      this.transport.write(`${JSON.stringify({ id, cmd, params })}\n`).catch((failure: unknown) => {
        this.pending.delete(id);
        reject(failure instanceof Error ? failure : new BackendError(String(failure)));
      });
    });
  }

  private handleChunk(chunk: string): void {
    this.buffer += chunk;
    const lines = this.buffer.split("\n");
    this.buffer = lines.pop() ?? "";
    lines.filter((line) => line.trim() !== "").forEach((line) => this.handleLine(line));
  }

  private handleLine(line: string): void {
    const message = parseMessage(line);
    if (!message) return;
    if (message.type === "ready") {
      this.resolveReady();
      return;
    }
    if (typeof message.id !== "number") return;
    const entry = this.pending.get(message.id);
    if (!entry) return;

    if (message.type === "progress") {
      entry.onProgress?.({ stage: String(message.stage), pct: Number(message.pct) });
    } else if (message.type === "result") {
      this.pending.delete(message.id);
      const { id: _id, type: _type, ...data } = message;
      entry.resolve(data);
    } else if (message.type === "error") {
      this.pending.delete(message.id);
      entry.reject(
        new BackendError(String(message.message), String(message.code ?? "failed"), message.details as ErrorDetails | undefined),
      );
    }
  }

  private handleClose(): void {
    if (this.stopped) return;
    this.stopped = true;
    this.rejectReady(stoppedError());
    this.pending.forEach((entry) => entry.reject(stoppedError()));
    this.pending.clear();
    this.closeListeners.forEach((listener) => listener());
  }
}

function parseMessage(line: string): Incoming | null {
  try {
    const parsed: unknown = JSON.parse(line);
    return typeof parsed === "object" && parsed !== null ? (parsed as Incoming) : null;
  } catch {
    return null;
  }
}
