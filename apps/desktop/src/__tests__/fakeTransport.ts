import type { Transport } from "../backend/Backend";

export class FakeTransport implements Transport {
  written: string[] = [];
  closed = false;
  private dataListener: ((chunk: string) => void) | null = null;
  private closeListeners: Array<() => void> = [];

  async write(data: string): Promise<void> {
    this.written.push(data);
  }

  onData(listener: (chunk: string) => void): void {
    this.dataListener = listener;
  }

  onClose(listener: () => void): void {
    this.closeListeners.push(listener);
  }

  async close(): Promise<void> {
    this.emitClose();
  }

  emitChunk(chunk: string): void {
    this.dataListener?.(chunk);
  }

  emitMessage(message: object): void {
    this.emitChunk(`${JSON.stringify(message)}\n`);
  }

  emitClose(): void {
    this.closed = true;
    this.closeListeners.forEach((listener) => listener());
  }

  requests(): Array<{ id: number; cmd: string; params?: Record<string, unknown> }> {
    return this.written.map((line) => JSON.parse(line));
  }
}
