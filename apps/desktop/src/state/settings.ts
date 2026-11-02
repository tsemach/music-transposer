import type { Register, Source } from "../backend/protocol";

export interface Settings {
  source: Source;
  register: Register;
  audiveris?: string;
  musescore?: string;
  outDir?: string;
}

export const DEFAULT_SETTINGS: Settings = { source: "alto", register: "auto" };

const STORAGE_KEY = "ascurix.settings";
const SOURCES: Source[] = ["alto", "tenor"];
const REGISTERS: Register[] = ["auto", "same", "shifted"];

export function loadSettings(storage: Pick<Storage, "getItem">): Settings {
  try {
    const raw: unknown = JSON.parse(storage.getItem(STORAGE_KEY) ?? "null");
    if (typeof raw !== "object" || raw === null) return DEFAULT_SETTINGS;
    const stored = raw as Record<string, unknown>;
    return {
      source: SOURCES.find((value) => value === stored.source) ?? DEFAULT_SETTINGS.source,
      register: REGISTERS.find((value) => value === stored.register) ?? DEFAULT_SETTINGS.register,
      ...optionalString("audiveris", stored.audiveris),
      ...optionalString("musescore", stored.musescore),
      ...optionalString("outDir", stored.outDir),
    };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function saveSettings(storage: Pick<Storage, "setItem">, settings: Settings): void {
  storage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

function optionalString<K extends string>(key: K, value: unknown): Partial<Record<K, string>> {
  return typeof value === "string" && value !== "" ? ({ [key]: value } as Record<K, string>) : {};
}
