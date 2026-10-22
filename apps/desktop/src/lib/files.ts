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

/**
 * Read a picked or dropped file as UTF-8 text. FileReader rather than Blob.text():
 * files handed over by some drag sources and test doubles have no .text().
 */
export function readTextFile(file: File, maxBytes = MAX_IMPORT_BYTES): Promise<string> {
  if (file.size > maxBytes) return Promise.reject(new FileTooLargeError(file.size));
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () => reject(reader.error ?? new Error(`Couldn't read ${file.name}`));
    reader.readAsText(file, "utf-8");
  });
}

/** Today's date as YYYY-MM-DD in the user's own time zone, for export file names.
 *  (toISOString() is UTC: in India an export made before 05:30 got yesterday's date.) */
export function todayStamp(now = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}
