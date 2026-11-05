export type DocKey = "original" | "transposed";
export type SplitMode = "single" | "columns" | "rows";

export interface ViewerState {
  split: SplitMode;
  panes: [DocKey, DocKey];
  zoom: number;
  continuous: boolean;
}

export type ViewerAction =
  | { type: "setSplit"; split: SplitMode }
  | { type: "setPane"; pane: 0 | 1; doc: DocKey }
  | { type: "zoomIn" }
  | { type: "zoomOut" }
  | { type: "toggleContinuous" }
  | { type: "documentChosen" }
  | { type: "resultReady" };

export const INITIAL_VIEWER: ViewerState = {
  split: "single",
  panes: ["original", "original"],
  zoom: 1,
  continuous: true,
};

export const ZOOM_STEPS = [0.5, 0.75, 1, 1.25, 1.5, 2, 3];

export function viewerReducer(state: ViewerState, action: ViewerAction): ViewerState {
  switch (action.type) {
    case "setSplit":
      return { ...state, split: action.split };
    case "setPane": {
      const panes: [DocKey, DocKey] = action.pane === 0 ? [action.doc, state.panes[1]] : [state.panes[0], action.doc];
      return { ...state, panes };
    }
    case "zoomIn":
      return { ...state, zoom: ZOOM_STEPS.find((step) => step > state.zoom) ?? state.zoom };
    case "zoomOut":
      return { ...state, zoom: [...ZOOM_STEPS].reverse().find((step) => step < state.zoom) ?? state.zoom };
    case "toggleContinuous":
      return { ...state, continuous: !state.continuous };
    case "documentChosen":
      return { ...state, panes: ["original", "original"] };
    case "resultReady":
      return { ...state, split: state.split === "single" ? "columns" : state.split, panes: [state.panes[0], "transposed"] };
  }
}

export function isContinuing(state: ViewerState): boolean {
  return state.continuous && state.split !== "single" && state.panes[0] === state.panes[1];
}
