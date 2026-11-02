import type { Finding } from "../backend/protocol";

export function FindingsList({ findings }: { findings: Finding[] }) {
  return (
    <ul className="findings">
      {findings.map((finding, index) => (
        <li key={`${finding.check}-${finding.measure}-${index}`} className={`finding finding-${finding.severity}`}>
          <span className="badge">{finding.severity === "error" ? "Error" : "Check"}</span>
          <span className="finding-bar">{finding.measure ? `Bar ${finding.measure}` : "Whole score"}</span>
          <span>{finding.message}</span>
        </li>
      ))}
    </ul>
  );
}
