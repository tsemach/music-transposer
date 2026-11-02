import { describeInterval } from "../lib/describeInterval";

test.each([
  ["P4", "same", "Up a perfect 4th (same sounding pitch)"],
  ["-P5", "shifted", "Down a perfect 5th (sounds an octave lower)"],
  ["-P4", "same", "Down a perfect 4th (same sounding pitch)"],
  ["P5", "shifted", "Up a perfect 5th (sounds an octave higher)"],
] as const)("%s (%s) reads as plain language", (name, register, expected) => {
  expect(describeInterval(name, register)).toBe(expected);
});

test("an unexpected interval falls back to its raw name", () => {
  expect(describeInterval("M2", "same")).toBe("M2");
});
