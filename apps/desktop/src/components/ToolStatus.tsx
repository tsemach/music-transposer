import type { DoctorResult } from "../backend/protocol";

export type ToolKey = keyof DoctorResult;

const TOOLS: Array<{ key: ToolKey; label: string }> = [
  { key: "audiveris", label: "Audiveris" },
  { key: "musescore", label: "MuseScore" },
];

interface Props {
  doctor: DoctorResult | null;
  onLocate: (tool: ToolKey, label: string) => void;
}

export function ToolStatus({ doctor, onLocate }: Props) {
  return (
    <ul className="tools" aria-label="Tools">
      {TOOLS.map(({ key, label }) => {
        const path = doctor?.[key];
        const state = doctor === null ? "checking" : path ? "found" : "missing";
        const text = state === "checking" ? "checking…" : state === "found" ? "found" : "not found";
        return (
          <li key={key} className={`tool tool-${state}`} title={path ?? undefined}>
            <span className="tool-dot" aria-hidden="true" />
            <span>{`${label}: ${text}`}</span>
            {state === "missing" && (
              <button type="button" className="button button-small" onClick={() => onLocate(key, label)}>
                {`Locate ${label}…`}
              </button>
            )}
          </li>
        );
      })}
    </ul>
  );
}
