import { useEffect, useState } from "react";

import type { PdfDocument, PdfLoader } from "../lib/pdf/types";

export type PdfLoadState =
  | { status: "empty" }
  | { status: "loading" }
  | { status: "ready"; doc: PdfDocument }
  | { status: "error"; message: string };

export function usePdfDocument(path: string | null, load: PdfLoader): PdfLoadState {
  const [state, setState] = useState<{ path: string | null; value: PdfLoadState }>({
    path: null,
    value: { status: "empty" },
  });

  useEffect(() => {
    if (!path) return;
    let stale = false;
    let loaded: PdfDocument | null = null;
    load(path)
      .then((doc) => {
        if (stale) return doc.destroy();
        loaded = doc;
        setState({ path, value: { status: "ready", doc } });
      })
      .catch((error: unknown) => {
        if (!stale) setState({ path, value: { status: "error", message: errorText(error) } });
      });
    return () => {
      stale = true;
      loaded?.destroy();
    };
  }, [path, load]);

  if (!path) return { status: "empty" };
  return state.path === path ? state.value : { status: "loading" };
}

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
