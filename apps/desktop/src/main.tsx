import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App, type AppProps } from "./App";
import { mockTransportFor } from "./backend/mockScenarios";
import "./styles.css";

const mockScenario = import.meta.env.DEV ? new URLSearchParams(location.search).get("mock") : null;

const mockProps: AppProps | null = mockScenario
  ? {
      createTransport: mockTransportFor(mockScenario),
      pickPdf: async () => "/home/me/Music/שיר ראשון - Gymnopédie.pdf",
      pickExecutable: async () => "/mock/Audiveris",
      pickFolder: async () => "/home/me/Music/Tenor parts",
      openPath: async () => undefined,
      revealPath: async () => undefined,
    }
  : null;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App {...(mockProps ?? {})} />
  </StrictMode>,
);
