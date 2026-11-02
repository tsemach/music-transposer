import { useEffect, useState } from "react";

import type { Transport } from "./backend/Backend";
import type { DoctorResult, PipelineParams, Register, Source } from "./backend/protocol";
import { createTauriTransport } from "./backend/tauriTransport";
import { ErrorBanner } from "./components/ErrorBanner";
import { FailureCard } from "./components/FailureCard";
import { FilePicker } from "./components/FilePicker";
import { ModePicker } from "./components/ModePicker";
import { ProgressView } from "./components/ProgressView";
import { ResultCard } from "./components/ResultCard";
import { ToolStatus, type ToolKey } from "./components/ToolStatus";
import { logToShell } from "./lib/diagnostics";
import { isPdf } from "./lib/fileName";
import * as tauriActions from "./lib/tauriActions";
import { loadSettings, saveSettings, type Settings } from "./state/settings";
import { useBackend, type BackendStatus } from "./state/useBackend";
import { useJobRunner } from "./state/useJobRunner";

export interface AppProps {
  createTransport?: () => Promise<Transport>;
  pickPdf?: () => Promise<string | null>;
  pickExecutable?: (label: string) => Promise<string | null>;
  pickFolder?: () => Promise<string | null>;
  openPath?: (path: string) => Promise<void>;
  revealPath?: (path: string) => Promise<void>;
}

const STATUS_TEXT: Record<BackendStatus, string> = {
  starting: "Starting engine…",
  ready: "Engine ready",
  stopped: "Engine stopped",
};

export function App({
  createTransport = createTauriTransport,
  pickPdf = tauriActions.pickPdf,
  pickExecutable = tauriActions.pickExecutable,
  pickFolder = tauriActions.pickFolder,
  openPath = tauriActions.openFile,
  revealPath = tauriActions.revealFile,
}: AppProps = {}) {
  const [settings, setSettings] = useState<Settings>(() => loadSettings(localStorage));
  const [pdf, setPdf] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [doctor, setDoctor] = useState<DoctorResult | null>(null);
  const { status, backend, restart } = useBackend(createTransport);
  const { job, run, cancel, reset } = useJobRunner(backend);

  useEffect(() => saveSettings(localStorage, settings), [settings]);
  useEffect(() => logToShell(`engine ${status}`), [status]);
  useEffect(() => {
    if (doctor) logToShell(`tools audiveris=${doctor.audiveris ?? "none"} musescore=${doctor.musescore ?? "none"}`);
  }, [doctor]);

  useEffect(() => {
    if (!backend) return;
    let stale = false;
    backend
      .call<DoctorResult>("doctor", { audiveris: settings.audiveris, musescore: settings.musescore })
      .result.then((found) => !stale && setDoctor(found))
      .catch(() => !stale && setDoctor(null));
    return () => {
      stale = true;
    };
  }, [backend, settings.audiveris, settings.musescore]);

  const update = (patch: Partial<Settings>) => setSettings((current) => ({ ...current, ...patch }));

  const choosePdf = async () => {
    const path = await pickPdf();
    if (!path) return;
    if (!isPdf(path)) {
      setNotice("Please choose a PDF file.");
      return;
    }
    setNotice(null);
    setPdf(path);
  };

  const locate = async (tool: ToolKey, label: string) => {
    const path = await pickExecutable(label);
    if (path) update({ [tool]: path });
  };

  const choosePdfFolder = async () => {
    const folder = await pickFolder();
    if (folder) update({ outDir: folder });
  };

  const convert = (force: boolean) => {
    if (!pdf) return;
    const params: PipelineParams = {
      pdf,
      source: settings.source,
      register: settings.register,
      force,
      outDir: settings.outDir,
      audiveris: settings.audiveris,
      musescore: settings.musescore,
    };
    void run(params);
  };

  const target = settings.source === "alto" ? "Tenor" : "Alto";

  return (
    <main className="app">
      <header className="header">
        <div>
          <h1>Ascurix</h1>
          <p className="tagline">Transpose sheet music between alto and tenor saxophone</p>
        </div>
        <span role="status" className={`engine engine-${status}`}>
          {STATUS_TEXT[status]}
        </span>
      </header>

      <ToolStatus doctor={doctor} onLocate={locate} />
      {status === "stopped" && (
        <ErrorBanner message="The engine stopped unexpectedly." actionLabel="Restart" onAction={restart} />
      )}
      {notice && <ErrorBanner message={notice} onDismiss={() => setNotice(null)} />}
      {job.phase === "failed" && job.code !== "validation_failed" && (
        <ErrorBanner message={job.message} onDismiss={reset} />
      )}

      {job.phase === "running" && <ProgressView stage={job.stage} pct={job.pct} onCancel={cancel} />}
      {job.phase === "done" && (
        <ResultCard
          result={job.result}
          target={target}
          onOpenPdf={() => void openPath(job.result.pdf)}
          onReveal={() => void revealPath(job.result.pdf)}
          onReset={() => {
            setPdf(null);
            reset();
          }}
        />
      )}
      {job.phase === "failed" && job.code === "validation_failed" && (
        <FailureCard findings={job.findings} onForce={() => convert(true)} onBack={reset} />
      )}
      {(job.phase === "idle" || (job.phase === "failed" && job.code !== "validation_failed")) && (
        <form
          className="setup"
          onSubmit={(event) => {
            event.preventDefault();
            convert(false);
          }}
        >
          <FilePicker path={pdf} onChoose={choosePdf} />
          <ModePicker
            source={settings.source}
            register={settings.register}
            outDir={settings.outDir}
            onSource={(source: Source) => update({ source })}
            onRegister={(register: Register) => update({ register })}
            onPickFolder={choosePdfFolder}
            onResetFolder={() => update({ outDir: undefined })}
          />
          <div className="actions">
            <button type="submit" className="button button-primary" disabled={!pdf || status !== "ready"}>
              Convert
            </button>
          </div>
        </form>
      )}
    </main>
  );
}
