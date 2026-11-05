import { INITIAL_VIEWER, isContinuing, viewerReducer, type ViewerState } from "../state/viewerState";

const split: ViewerState = { ...INITIAL_VIEWER, split: "columns" };

test("a finished conversion opens the transposed part beside the original", () => {
  const next = viewerReducer(INITIAL_VIEWER, { type: "resultReady" });

  expect(next.split).toBe("columns");
  expect(next.panes).toEqual(["original", "transposed"]);
});

test("a finished conversion keeps a layout the user already chose", () => {
  expect(viewerReducer({ ...INITIAL_VIEWER, split: "rows" }, { type: "resultReady" }).split).toBe("rows");
});

test("choosing a new file shows it in both panes", () => {
  const before: ViewerState = { ...split, panes: ["original", "transposed"] };

  expect(viewerReducer(before, { type: "documentChosen" }).panes).toEqual(["original", "original"]);
});

test("zoom moves through the steps and stops at both ends", () => {
  let state = INITIAL_VIEWER;
  for (let i = 0; i < 10; i += 1) state = viewerReducer(state, { type: "zoomIn" });
  expect(state.zoom).toBe(3);
  for (let i = 0; i < 10; i += 1) state = viewerReducer(state, { type: "zoomOut" });
  expect(state.zoom).toBe(0.5);
});

test("continuous reading needs a split and the same document in both panes", () => {
  expect(isContinuing(INITIAL_VIEWER)).toBe(false);
  expect(isContinuing(split)).toBe(true);
  expect(isContinuing({ ...split, panes: ["original", "transposed"] })).toBe(false);
  expect(isContinuing(viewerReducer(split, { type: "toggleContinuous" }))).toBe(false);
});
