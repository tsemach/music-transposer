import { open } from "@tauri-apps/plugin-dialog";
import { openPath, revealItemInDir } from "@tauri-apps/plugin-opener";

async function pickOne(options: Parameters<typeof open>[0]): Promise<string | null> {
  const selected = await open({ multiple: false, ...options });
  return typeof selected === "string" ? selected : null;
}

export const pickPdf = () => pickOne({ directory: false, filters: [{ name: "PDF", extensions: ["pdf"] }] });
export const pickExecutable = (label: string) => pickOne({ directory: false, title: `Locate ${label}` });
export const pickFolder = () => pickOne({ directory: true, title: "Choose where to save the results" });
export const openFile = (path: string) => openPath(path);
export const revealFile = (path: string) => revealItemInDir(path);
