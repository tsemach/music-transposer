import type { KeyboardEvent, PointerEvent, RefObject } from "react";

import type { SplitMode } from "../../state/viewerState";

const MIN = 0.2;
const MAX = 0.8;
const KEY_STEP = 0.05;

interface Props {
  split: Exclude<SplitMode, "single">;
  ratio: number;
  containerRef: RefObject<HTMLElement | null>;
  onRatio: (ratio: number) => void;
}

export function SplitHandle({ split, ratio, containerRef, onRatio }: Props) {
  const horizontal = split === "columns";
  const clamp = (value: number) => Math.min(MAX, Math.max(MIN, value));

  const drag = (event: PointerEvent<HTMLDivElement>) => {
    const box = containerRef.current?.getBoundingClientRect();
    if (!box || event.buttons === 0) return;
    onRatio(clamp(horizontal ? (event.clientX - box.left) / box.width : (event.clientY - box.top) / box.height));
  };

  const nudge = (event: KeyboardEvent<HTMLDivElement>) => {
    const forward = horizontal ? "ArrowRight" : "ArrowDown";
    const backward = horizontal ? "ArrowLeft" : "ArrowUp";
    if (event.key === forward) onRatio(clamp(ratio + KEY_STEP));
    if (event.key === backward) onRatio(clamp(ratio - KEY_STEP));
  };

  return (
    <div
      role="separator"
      tabIndex={0}
      aria-label="Resize panes"
      aria-orientation={horizontal ? "vertical" : "horizontal"}
      aria-valuemin={MIN * 100}
      aria-valuemax={MAX * 100}
      aria-valuenow={Math.round(ratio * 100)}
      className={`split-handle split-handle-${split}`}
      onPointerDown={(event) => event.currentTarget.setPointerCapture(event.pointerId)}
      onPointerMove={drag}
      onKeyDown={nudge}
    />
  );
}
