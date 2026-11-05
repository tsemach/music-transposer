import { useEffect, useReducer, useState } from "react";

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
import { Viewer } from "./components/viewer/Viewer";
import { logToShell } from "./lib/diagnostics";
import { isPdf } from "./lib/fileName";
import { loadPdfWithPdfjs } from "./lib/pdf/pdfjsLoader";
import type { PdfLoader } from "./lib/pdf/types";
import * as tauriActions from "./lib/tauriActions";
import { loadSettings, saveSettings, type Settings } from "./state/settings";
import { useBackend, type BackendStatus } from "./state/useBackend";
import { useJobRunner } from "./state/useJobRunner";
import { usePdfDocument } from "./state/usePdfDocument";
import { INITIAL_VIEWER, viewerReducer } from "./state/viewerState";

export interface AppProps {
  createTransport?: () => Promise<Transport>;
  pickPdf?: () => Promise<string | null>;
  pickExecutable?: (label: string) => Promise<string | null>;
  pickFolder?: () => Promise<string | null>;
  openPath?: (path: string) => Promise<void>;
  revealPath?: (path: string) => Promise<void>;
  loadPdf?: PdfLoader;
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
  loadPdf = loadPdfWithPdfjs,
}: AppProps = {}) {
  const [settings, setSettings] = useState<Settings>(() => loadSettings(localStorage));
  const [pdf, setPdf] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [doctor, setDoctor] = useState<DoctorResult | null>(null);
  const { status, backend, restart } = useBackend(createTransport);
  const { job, run, cancel, reset } = useJobRunner(backend);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [viewer, dispatchViewer] = useReducer(viewerReducer, INITIAL_VIEWER);
  const resultPdf = job.phase === "done" ? job.result.pdf : null;
  const loads = { original: usePdfDocument(pdf, loadPdf), transposed: usePdfDocument(resultPdf, loadPdf) };

  useEffect(() => {
    if (resultPdf) dispatchViewer({ type: "resultReady" });
  }, [resultPdf]);

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
    dispatchViewer({ type: "documentChosen" });
  };

  const locate = async (tool: ToolKey, label: string) => {
    const path = await pickExecutable(label);
    if (path) update({ [tool]: path });
  };

  const choosePdfFolder = async () => {
    const folder = await pickFolder();
    if (folder) update({ outDir: folder });
  };

  const attempt = async (action: () => Promise<void>, failure: string) => {
    try {
      await action();
    } catch (error) {
      setNotice(`${failure}: ${error instanceof Error ? error.message : String(error)}`);
    }
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

  const emptyState = (
    <div className="empty-state">
      <p>Your sheet music appears here.</p>
      <button type="button" className="button button-primary" onClick={() => void choosePdf()}>
        Open a PDF to begin
      </button>
    </div>
  );

  return (
    <div className="shell">
      <header className="topbar">
        <button
          type="button"
          className="icon-button"
          aria-label={sidebarOpen ? "Hide side panel" : "Show side panel"}
          aria-pressed={sidebarOpen}
          onClick={() => setSidebarOpen((open) => !open)}
        >
          ☰
        </button>
        <h1>Music Transpose</h1>
        <span role="status" className={`engine engine-${status}`}>
          {STATUS_TEXT[status]}
        </span>
      </header>

      <div className="body">
        {sidebarOpen && (
          <aside className="sidebar" aria-label="Transpose">
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
                onOpenPdf={() => void attempt(() => openPath(job.result.pdf), "Could not open the PDF")}
                onReveal={() => void attempt(() => revealPath(job.result.pdf), "Could not show the folder")}
                onReset={() => {
                  setPdf(null);
                  dispatchViewer({ type: "documentChosen" });
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
          </aside>
        )}
        <main className="stage">
          <Viewer state={viewer} dispatch={dispatchViewer} loads={loads} emptyState={emptyState} />
        </main>
      </div>
    </div>
  );
}
