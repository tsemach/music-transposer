import { invoke } from "@tauri-apps/api/core";

export function logToShell(message: string): void {
  if (typeof window === "undefined" || !("__TAURI_INTERNALS__" in window)) return;
  invoke("ui_log", { message }).catch(() => undefined);
}
