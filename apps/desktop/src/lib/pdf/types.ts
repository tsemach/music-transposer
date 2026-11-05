export interface PageRender {
  cancel: () => void;
  done: Promise<void>;
}

export interface PdfDocument {
  pageAspects: number[];
  renderPage: (pageNumber: number, canvas: HTMLCanvasElement, cssWidth: number) => PageRender;
  destroy: () => void;
}

export type PdfLoader = (path: string) => Promise<PdfDocument>;
