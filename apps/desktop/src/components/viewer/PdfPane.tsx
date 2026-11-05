import { useEffect, useState, type ReactNode, type RefObject } from "react";

import type { PdfLoadState } from "../../state/usePdfDocument";
import type { DocKey } from "../../state/viewerState";
import { PdfPageCanvas } from "./PdfPageCanvas";

const PAGE_PADDING = 24;
const FALLBACK_WIDTH = 800;

interface Props {
  label: string;
  doc: DocKey;
  transposedAvailable: boolean;
  load: PdfLoadState;
  zoom: number;
  scrollRef: RefObject<HTMLDivElement | null>;
  onDocChange: (doc: DocKey) => void;
  placeholder: ReactNode;
}

export function PdfPane({ label, doc, transposedAvailable, load, zoom, scrollRef, onDocChange, placeholder }: Props) {
  const [root, setRoot] = useState<HTMLDivElement | null>(null);
  const [paneWidth, setPaneWidth] = useState(FALLBACK_WIDTH);

  useEffect(() => {
    if (!root || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(([entry]) => entry && setPaneWidth(entry.contentRect.width));
    observer.observe(root);
    return () => observer.disconnect();
  }, [root]);

  const pageWidth = Math.max(120, Math.round((paneWidth - PAGE_PADDING * 2) * zoom));

  return (
    <section className="pane" aria-label={label}>
      <header className="pane-header">
        <select aria-label={`${label} document`} value={doc} onChange={(event) => onDocChange(event.target.value as DocKey)}>
          <option value="original">Original</option>
          <option value="transposed" disabled={!transposedAvailable}>
            Transposed
          </option>
        </select>
        {load.status === "ready" && <span className="hint">{`${load.doc.pageAspects.length} pages`}</span>}
      </header>
      <div
        className="pane-scroll"
        tabIndex={0}
        ref={(element) => {
          setRoot(element);
          scrollRef.current = element;
        }}
      >
        {load.status === "ready" ? (
          <div className="pages">
            {load.doc.pageAspects.map((_, index) => (
              <PdfPageCanvas key={index} doc={load.doc} pageNumber={index + 1} width={pageWidth} root={root} />
            ))}
          </div>
        ) : (
          <div className="pane-message">{messageFor(load, placeholder)}</div>
        )}
      </div>
    </section>
  );
}

function messageFor(load: PdfLoadState, placeholder: ReactNode): ReactNode {
  if (load.status === "loading") return "Loading sheet music…";
  if (load.status === "error") return <span role="alert">{`Could not display the PDF: ${load.message}`}</span>;
  return placeholder;
}
