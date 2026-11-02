import { baseName, dirName, isPdf } from "../lib/fileName";

test("baseName handles unix and windows separators and Hebrew names", () => {
  expect(baseName("/home/me/שיר ראשון.pdf")).toBe("שיר ראשון.pdf");
  expect(baseName("C:\\Users\\me\\Music\\song.pdf")).toBe("song.pdf");
  expect(baseName("plain.pdf")).toBe("plain.pdf");
});

test("isPdf is case-insensitive and requires the extension", () => {
  expect(isPdf("/a/b/Song.PDF")).toBe(true);
  expect(isPdf("/a/b/song.pdf")).toBe(true);
  expect(isPdf("/a/b/song.png")).toBe(false);
  expect(isPdf("/a/b/pdf")).toBe(false);
});

test("dirName returns the containing folder for unix and windows paths", () => {
  expect(dirName("/music/שיר.pdf")).toBe("/music");
  expect(dirName("C:\\Users\\me\\song.pdf")).toBe("C:\\Users\\me");
  expect(dirName("song.pdf")).toBe("");
});
