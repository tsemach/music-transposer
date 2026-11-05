import { useEffect, useRef, useState } from "react";

import type { PdfDocument } from "../../lib/pdf/types";

interface Props {
  doc: PdfDocument;
  pageNumber: number;
  width: number;
  root: HTMLElement | null;
}

export function PdfPageCanvas({ doc, pageNumber, width, root }: Props) {
  const holder = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [near, setNear] = useState(typeof IntersectionObserver === "undefined");
  const height = width * (doc.pageAspects[pageNumber - 1] ?? 1.414);

  useEffect(() => {
    if (typeof IntersectionObserver === "undefined" || !holder.current) return;
    const observer = new IntersectionObserver(([entry]) => entry?.isIntersecting && setNear(true), {
      root,
      rootMargin: "800px 0px",
    });
    observer.observe(holder.current);
    return () => observer.disconnect();
  }, [root]);

  useEffect(() => {
    if (!near || !canvas.current || width <= 0) return;
    const render = doc.renderPage(pageNumber, canvas.current, width);
    render.done.catch(() => undefined);
    return render.cancel;
  }, [near, doc, pageNumber, width]);

  return (
    <div ref={holder} className="page" style={{ width, height }} data-page={pageNumber}>
      <canvas ref={canvas} aria-label={`Page ${pageNumber}`} />
    </div>
  );
}
