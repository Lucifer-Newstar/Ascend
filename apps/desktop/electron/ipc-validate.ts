/**
 * Shape checks for IPC payloads from the renderer, which main treats as untrusted input.
 */
import path from "node:path";

import type { ExportSaveRequest } from "@ascend/shared";

/** Bigger than any export ASCEND writes (years of history is a few MB). */
export const MAX_EXPORT_BYTES = 64 * 1024 * 1024;
const MAX_NAME_LENGTH = 120;

/**
 * export:save: `content` must be a string under MAX_EXPORT_BYTES and `defaultName` a
 * plain file name (no folders, no NUL). The save dialog still lets the user pick any
 * location; this only stops the renderer from writing other types or huge payloads, or
 * pre-filling a path outside the dialog's default folder (review L11).
 */
export function validateExportSave(req: unknown): ExportSaveRequest {
  if (!req || typeof req !== "object") throw new Error("invalid export request");
  const { defaultName, content } = req as Record<string, unknown>;
  if (typeof content !== "string") throw new Error("export content must be text");
  if (Buffer.byteLength(content, "utf8") > MAX_EXPORT_BYTES) throw new Error("export is too large");
  if (
    typeof defaultName !== "string" ||
    !defaultName ||
    defaultName.length > MAX_NAME_LENGTH ||
    defaultName.includes("\0") ||
    defaultName !== path.basename(defaultName) ||
    defaultName !== path.win32.basename(defaultName) ||
    defaultName === "." ||
    defaultName === ".."
  ) {
    throw new Error("invalid export file name");
  }
  return { defaultName, content };
}
