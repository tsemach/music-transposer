import { useRef, useState, type ReactNode } from "react";

import { useLinkedScroll } from "../../state/useLinkedScroll";
import type { PdfLoadState } from "../../state/usePdfDocument";
import { isContinuing, type DocKey, type ViewerAction, type ViewerState } from "../../state/viewerState";
import { PdfPane } from "./PdfPane";
import { SplitHandle } from "./SplitHandle";
import { ViewerToolbar } from "./ViewerToolbar";

interface Props {
  state: ViewerState;
  dispatch: (action: ViewerAction) => void;
  loads: Record<DocKey, PdfLoadState>;
  emptyState: ReactNode;
}

export function Viewer({ state, dispatch, loads, emptyState }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const firstScroll = useRef<HTMLDivElement>(null);
  const secondScroll = useRef<HTMLDivElement>(null);
  const [ratio, setRatio] = useState(0.5);
  const split = state.split;
  const continuing = isContinuing(state);
  useLinkedScroll(continuing, firstScroll, secondScroll);

  const pane = (index: 0 | 1, label: string, scrollRef: typeof firstScroll) => (
    <PdfPane
      label={label}
      doc={state.panes[index]}
      transposedAvailable={loads.transposed.status !== "empty"}
      load={loads[state.panes[index]]}
      zoom={state.zoom}
      scrollRef={scrollRef}
      onDocChange={(doc) => dispatch({ type: "setPane", pane: index, doc })}
      placeholder={index === 0 ? emptyState : "Nothing to show yet."}
    />
  );

  const template = `${ratio}fr 6px ${1 - ratio}fr`;
  return (
    <div className="viewer">
      <ViewerToolbar
        split={split}
        zoom={state.zoom}
        canContinue={split !== "single" && state.panes[0] === state.panes[1]}
        continuing={continuing}
        onSplit={(next) => dispatch({ type: "setSplit", split: next })}
        onZoomIn={() => dispatch({ type: "zoomIn" })}
        onZoomOut={() => dispatch({ type: "zoomOut" })}
        onToggleContinue={() => dispatch({ type: "toggleContinuous" })}
      />
      <div
        ref={container}
        className={`panes panes-${split}`}
        style={split === "columns" ? { gridTemplateColumns: template } : split === "rows" ? { gridTemplateRows: template } : undefined}
      >
        {pane(0, "First pane", firstScroll)}
        {split !== "single" && (
          <>
            <SplitHandle split={split} ratio={ratio} containerRef={container} onRatio={setRatio} />
            {pane(1, "Second pane", secondScroll)}
          </>
        )}
      </div>
    </div>
  );
}
