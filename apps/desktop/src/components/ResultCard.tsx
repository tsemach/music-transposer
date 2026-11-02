import type { PipelineResult } from "../backend/protocol";
import { describeInterval } from "../lib/describeInterval";
import { baseName, dirName } from "../lib/fileName";
import { FindingsList } from "./FindingsList";

interface Props {
  result: PipelineResult;
  target: "Alto" | "Tenor";
  onOpenPdf: () => void;
  onReveal: () => void;
  onReset: () => void;
}

export function ResultCard({ result, target, onOpenPdf, onReveal, onReset }: Props) {
  const hasErrors = result.findings.some((finding) => finding.severity === "error");
  return (
    <section className="card card-success">
      <h2>{`${target} part ready`}</h2>
      <p className="interval">{describeInterval(result.interval.name, result.interval.register)}</p>
      <p className="saved">
        Saved as <strong dir="auto">{baseName(result.pdf)}</strong> in <span dir="auto">{dirName(result.pdf)}</span>
      </p>
      {hasErrors && (
        <p className="caution">Converted despite errors in the scanned music. Check the result carefully.</p>
      )}
      {result.interval.outOfRange > 0 && (
        <p className="caution">{`${result.interval.outOfRange} notes fall outside the usual range of the ${target.toLowerCase()} saxophone.`}</p>
      )}
      {result.warnings.map((warning) => (
        <p key={warning} className="caution">
          {warning}
        </p>
      ))}
      {result.findings.length > 0 && (
        <details className="options">
          <summary>{`${result.findings.length} ${result.findings.length === 1 ? "thing" : "things"} to check in the original`}</summary>
          <FindingsList findings={result.findings} />
        </details>
      )}
      <div className="actions">
        <button type="button" className="button button-quiet" onClick={onReset}>
          Convert another
        </button>
        <button type="button" className="button" onClick={onReveal}>
          Show in folder
        </button>
        <button type="button" className="button button-primary" onClick={onOpenPdf}>
          Open PDF
        </button>
      </div>
    </section>
  );
}
