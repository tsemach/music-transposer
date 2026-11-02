import { useCallback, useEffect, useState } from "react";

import { Backend, type Transport } from "../backend/Backend";

export type BackendStatus = "starting" | "ready" | "stopped";

interface Handle {
  status: BackendStatus;
  backend: Backend | null;
}

export function useBackend(createTransport: () => Promise<Transport>) {
  const [generation, setGeneration] = useState(0);
  const [handle, setHandle] = useState<Handle>({ status: "starting", backend: null });

  useEffect(() => {
    let disposed = false;
    let active: Backend | null = null;
    setHandle({ status: "starting", backend: null });

    createTransport()
      .then(async (transport) => {
        const backend = new Backend(transport);
        active = backend;
        if (disposed) {
          void backend.close();
          return;
        }
        backend.onClose(() => {
          if (!disposed) setHandle({ status: "stopped", backend: null });
        });
        await backend.ready();
        if (!disposed) setHandle({ status: "ready", backend });
      })
      .catch(() => {
        if (!disposed) setHandle({ status: "stopped", backend: null });
      });

    return () => {
      disposed = true;
      void active?.close();
    };
  }, [createTransport, generation]);

  const restart = useCallback(() => setGeneration((value) => value + 1), []);
  return { ...handle, restart };
}
