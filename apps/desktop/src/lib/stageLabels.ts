const LABELS: Record<string, string> = {
  starting: "Starting",
  omr: "Reading the sheet",
  validate: "Checking the result",
  transpose: "Transposing",
  render: "Engraving the PDF",
  done: "Finishing",
};

export function stageLabel(stage: string): string {
  return LABELS[stage] ?? stage;
}
