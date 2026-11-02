import { stageLabel } from "../lib/stageLabels";

interface Props {
  stage: string;
  pct: number;
  onCancel: () => void;
}

export function ProgressView({ stage, pct, onCancel }: Props) {
  return (
    <section className="card">
      <h2>{stageLabel(stage)}…</h2>
      <div
        role="progressbar"
        aria-label="Conversion progress"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
        className="progress"
      >
        <div className="progress-bar" style={{ width: `${pct}%` }} />
      </div>
      <button type="button" className="button button-quiet" onClick={onCancel}>
        Cancel
      </button>
    </section>
  );
}
