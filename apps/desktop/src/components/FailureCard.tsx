import type { Finding } from "../backend/protocol";
import { FindingsList } from "./FindingsList";

interface Props {
  findings: Finding[];
  onForce: () => void;
  onBack: () => void;
}

export function FailureCard({ findings, onForce, onBack }: Props) {
  return (
    <section className="card">
      <h2>Problems found in the scanned music</h2>
      <p>
        The sheet was read, but these bars look wrong. Review them before trusting a converted part: any mistake would
        be carried into the new key.
      </p>
      <FindingsList findings={findings} />
      <div className="actions">
        <button type="button" className="button" onClick={onBack}>
          Choose another PDF
        </button>
        <button type="button" className="button button-primary" onClick={onForce}>
          Convert anyway
        </button>
      </div>
    </section>
  );
}
