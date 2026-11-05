import { ZOOM_STEPS, type SplitMode } from "../../state/viewerState";

interface Props {
  split: SplitMode;
  zoom: number;
  canContinue: boolean;
  continuing: boolean;
  onSplit: (split: SplitMode) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onToggleContinue: () => void;
}

const LAYOUTS: Array<{ value: SplitMode; label: string; glyph: string }> = [
  { value: "single", label: "Single view", glyph: "▭" },
  { value: "columns", label: "Side by side", glyph: "◫" },
  { value: "rows", label: "Top and bottom", glyph: "⬒" },
];

export function ViewerToolbar({ split, zoom, canContinue, continuing, onSplit, onZoomIn, onZoomOut, onToggleContinue }: Props) {
  return (
    <div className="viewer-toolbar" role="toolbar" aria-label="View">
      <div className="icon-group">
        {LAYOUTS.map(({ value, label, glyph }) => (
          <button
            key={value}
            type="button"
            className="icon-button"
            aria-label={label}
            title={label}
            aria-pressed={split === value}
            onClick={() => onSplit(value)}
          >
            {glyph}
          </button>
        ))}
      </div>
      {canContinue && (
        <label className="check" title="The second pane shows what comes right after the first, so you can play on without scrolling.">
          <input type="checkbox" checked={continuing} onChange={onToggleContinue} />
          Continue reading
        </label>
      )}
      <div className="icon-group zoom">
        <button type="button" className="icon-button" aria-label="Zoom out" disabled={zoom <= ZOOM_STEPS[0]!} onClick={onZoomOut}>
          −
        </button>
        <span className="zoom-level">{`Zoom ${Math.round(zoom * 100)}%`}</span>
        <button type="button" className="icon-button" aria-label="Zoom in" disabled={zoom >= ZOOM_STEPS.at(-1)!} onClick={onZoomIn}>
          +
        </button>
      </div>
    </div>
  );
}
