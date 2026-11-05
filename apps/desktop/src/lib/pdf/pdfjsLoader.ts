import type { PDFDocumentProxy } from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

import { readPdfBytes } from "../tauriActions";
import type { PageRender, PdfDocument, PdfLoader } from "./types";

export const loadPdfWithPdfjs: PdfLoader = async (path) => {
  const pdfjs = await import("pdfjs-dist");
  pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;
  const data = await readPdfBytes(path);
  const pdf = await pdfjs.getDocument({ data }).promise;
  return wrap(pdf, await measureAspects(pdf));
};

async function measureAspects(pdf: PDFDocumentProxy): Promise<number[]> {
  const aspects: number[] = [];
  for (let number = 1; number <= pdf.numPages; number += 1) {
    const { width, height } = (await pdf.getPage(number)).getViewport({ scale: 1 });
    aspects.push(height / width);
  }
  return aspects;
}

function wrap(pdf: PDFDocumentProxy, pageAspects: number[]): PdfDocument {
  return {
    pageAspects,
    destroy: () => void pdf.destroy(),
    renderPage: (pageNumber, canvas, cssWidth): PageRender => {
      let cancelled = false;
      let cancelTask = () => {};
      const done = (async () => {
        const page = await pdf.getPage(pageNumber);
        if (cancelled) return;
        const ratio = window.devicePixelRatio || 1;
        const base = page.getViewport({ scale: 1 });
        const viewport = page.getViewport({ scale: (cssWidth / base.width) * ratio });
        canvas.width = Math.floor(viewport.width);
        canvas.height = Math.floor(viewport.height);
        canvas.style.width = `${cssWidth}px`;
        const task = page.render({ canvasContext: canvas.getContext("2d")!, viewport });
        cancelTask = () => task.cancel();
        await task.promise;
      })().catch((error: unknown) => {
        if (!cancelled) throw error;
      });
      return {
        done,
        cancel: () => {
          cancelled = true;
          cancelTask();
        },
      };
    },
  };
}
