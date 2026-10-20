/**
 * File helpers for the renderer. In Electron a save goes through the preload
 * bridge (native Save dialog in main); in browser dev mode it falls back to a
 * download link. Reading uses the File API, which works in the sandbox.
 */

export async function saveFile(defaultName: string, content: string): Promise<string | null> {
  if (window.ascend) {
    const res = await window.ascend.saveExport({ defaultName, content });
    return res.saved ? res.path : null;
  }
  const url = URL.createObjectURL(new Blob([content], { type: "text/plain" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: defaultName });
  a.click();
  URL.revokeObjectURL(url);
  return defaultName;
}

/** Same cap as the sidecar (20 MB of text). */
export const MAX_IMPORT_BYTES = 20_000_000;

export class FileTooLargeError extends Error {
  constructor(readonly bytes: number) {
    super(`That file is ${(bytes / 1_000_000).toFixed(1)} MB; the limit is ${MAX_IMPORT_BYTES / 1_000_000} MB.`);
  }
}

export async function readTextFile(file: File, maxBytes = MAX_IMPORT_BYTES): Promise<string> {
  if (file.size > maxBytes) throw new FileTooLargeError(file.size);
  return file.text();
}

export function todayStamp(now = new Date()): string {
  return now.toISOString().slice(0, 10);
}
