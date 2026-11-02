import { DEFAULT_SETTINGS, loadSettings, saveSettings } from "../state/settings";

function storageWith(value: string | null) {
  const data = new Map<string, string>();
  if (value !== null) data.set("ascurix.settings", value);
  return {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, next: string) => void data.set(key, next),
  };
}

test("missing settings give the defaults", () => {
  expect(loadSettings(storageWith(null))).toEqual(DEFAULT_SETTINGS);
  expect(DEFAULT_SETTINGS).toMatchObject({ source: "alto", register: "auto" });
});

test("settings round trip", () => {
  const storage = storageWith(null);
  const settings = { source: "tenor", register: "shifted", audiveris: "/a/Audiveris", outDir: "/out" } as const;

  saveSettings(storage, settings);

  expect(loadSettings(storage)).toEqual(settings);
});

test("corrupt or invalid data falls back to defaults field by field", () => {
  expect(loadSettings(storageWith("{not json"))).toEqual(DEFAULT_SETTINGS);
  expect(loadSettings(storageWith(JSON.stringify({ source: "bass", register: 3, audiveris: 7 })))).toEqual(DEFAULT_SETTINGS);
  expect(loadSettings(storageWith(JSON.stringify({ source: "tenor" })))).toEqual({ ...DEFAULT_SETTINGS, source: "tenor" });
});
