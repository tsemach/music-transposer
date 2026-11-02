export function baseName(path: string): string {
  return path.split(/[\\/]/).pop() ?? path;
}

export function isPdf(path: string): boolean {
  return /\.pdf$/i.test(path);
}
