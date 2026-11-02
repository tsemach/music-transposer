const DESCRIPTIONS: Record<string, string> = {
  "P4:same": "Up a perfect 4th (same sounding pitch)",
  "-P5:shifted": "Down a perfect 5th (sounds an octave lower)",
  "-P4:same": "Down a perfect 4th (same sounding pitch)",
  "P5:shifted": "Up a perfect 5th (sounds an octave higher)",
};

export function describeInterval(name: string, register: "same" | "shifted"): string {
  return DESCRIPTIONS[`${name}:${register}`] ?? name;
}
