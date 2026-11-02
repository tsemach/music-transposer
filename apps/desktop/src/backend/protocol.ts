export type Severity = "error" | "warning";
export type Source = "alto" | "tenor";
export type Register = "auto" | "same" | "shifted";

export interface Finding {
  check: string;
  severity: Severity;
  measure: string | null;
  message: string;
}

export interface Interval {
  name: string;
  register: "same" | "shifted";
  outOfRange: number;
}

export interface PipelineParams {
  pdf: string;
  source: Source;
  register?: Register;
  force?: boolean;
  outDir?: string;
  audiveris?: string;
  musescore?: string;
}

export interface PipelineResult {
  originalMusicxml: string;
  tenorMusicxml: string;
  pdf: string;
  interval: Interval;
  findings: Finding[];
  warnings: string[];
}

export interface DoctorParams {
  audiveris?: string;
  musescore?: string;
}

export interface DoctorResult {
  audiveris: string | null;
  musescore: string | null;
}

export interface ProgressEvent {
  stage: string;
  pct: number;
}

export interface ErrorDetails {
  findings?: Finding[];
}

export class BackendError extends Error {
  readonly code: string;
  readonly details?: ErrorDetails;

  constructor(message: string, code = "failed", details?: ErrorDetails) {
    super(message);
    this.name = "BackendError";
    this.code = code;
    this.details = details;
  }
}
