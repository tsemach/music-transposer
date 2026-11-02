import { baseName } from "../lib/fileName";

interface Props {
  path: string | null;
  onChoose: () => void;
}

export function FilePicker({ path, onChoose }: Props) {
  return (
    <section className="step">
      <h2>
        <span className="step-number">1</span> Sheet music
      </h2>
      <div className="file-row">
        <button type="button" className="button" onClick={onChoose}>
          Choose PDF…
        </button>
        {path ? (
          <span className="file-name" dir="auto" title={path}>
            {baseName(path)}
          </span>
        ) : (
          <span className="hint">A clean, digitally made PDF works best.</span>
        )}
      </div>
    </section>
  );
}
