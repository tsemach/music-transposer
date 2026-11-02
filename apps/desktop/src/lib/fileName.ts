export function baseName(path: string): string {
  return path.split(/[\\/]/).pop() ?? path;
}

export function isPdf(path: string): boolean {
  return /\.pdf$/i.test(path);
}

export function dirName(path: string): string {
  const index = Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\"));
  return index === -1 ? "" : path.slice(0, index);
}
