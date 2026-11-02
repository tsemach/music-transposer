import type { Register, Source } from "../backend/protocol";

interface Props {
  source: Source;
  register: Register;
  outDir?: string;
  onSource: (source: Source) => void;
  onRegister: (register: Register) => void;
  onPickFolder: () => void;
  onResetFolder: () => void;
}

const DIRECTIONS: Array<{ value: Source; label: string }> = [
  { value: "alto", label: "Alto → Tenor" },
  { value: "tenor", label: "Tenor → Alto" },
];

export function ModePicker({ source, register, outDir, onSource, onRegister, onPickFolder, onResetFolder }: Props) {
  return (
    <section className="step">
      <h2>
        <span className="step-number">2</span> Convert
      </h2>
      <div role="radiogroup" aria-label="Direction" className="segmented">
        {DIRECTIONS.map(({ value, label }) => (
          <label key={value} className={source === value ? "segment segment-active" : "segment"}>
            <input type="radio" name="direction" value={value} checked={source === value} onChange={() => onSource(value)} />
            {label}
          </label>
        ))}
      </div>
      <details className="options">
        <summary>Options</summary>
        <label className="field">
          <span>Octave</span>
          <select value={register} onChange={(event) => onRegister(event.target.value as Register)}>
            <option value="auto">Automatic: best fit for the instrument range</option>
            <option value="same">Same sounding pitch</option>
            <option value="shifted">An octave away</option>
          </select>
        </label>
        <div className="field">
          <span>Save results</span>
          <span className="folder">
            <span dir="auto" title={outDir}>{outDir ?? "Next to the PDF"}</span>
            <button type="button" className="button button-small" onClick={onPickFolder}>
              Choose folder…
            </button>
            {outDir && (
              <button type="button" className="button button-small button-quiet" onClick={onResetFolder}>
                Reset
              </button>
            )}
          </span>
        </div>
      </details>
    </section>
  );
}
