import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";

async function pickOne(options: Parameters<typeof open>[0]): Promise<string | null> {
  const selected = await open({ multiple: false, ...options });
  return typeof selected === "string" ? selected : null;
}

export const pickPdf = () => pickOne({ directory: false, filters: [{ name: "PDF", extensions: ["pdf"] }] });
export const pickExecutable = (label: string) => pickOne({ directory: false, title: `Locate ${label}` });
export const pickFolder = () => pickOne({ directory: true, title: "Choose where to save the results" });
export const openFile = (path: string) => invoke<void>("open_in_host", { path, reveal: false });
export const revealFile = (path: string) => invoke<void>("open_in_host", { path, reveal: true });
export async function readPdfBytes(path: string): Promise<Uint8Array> {
  return new Uint8Array(await invoke<ArrayBuffer>("read_pdf_bytes", { path }));
}
