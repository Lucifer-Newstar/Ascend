/**
 * Shape checks for IPC payloads from the renderer, which main treats as untrusted input.
 */
import path from "node:path";

import type { ClipboardWriteRequest, ExportSaveRequest, ImageSaveRequest, VideoSaveRequest } from "@ascend/shared";

/** Bigger than any export ASCEND writes (years of history is a few MB). */
export const MAX_EXPORT_BYTES = 64 * 1024 * 1024;
const MAX_NAME_LENGTH = 120;

/**
 * export:save: `content` must be a string under MAX_EXPORT_BYTES and `defaultName` a
 * plain file name (no folders, no NUL). The save dialog still lets the user pick any
 * location; this only stops the renderer from writing other types or huge payloads, or
 * pre-filling a path outside the dialog's default folder (review L11).
 */
function plainName(defaultName: unknown): defaultName is string {
  return (
    typeof defaultName === "string" &&
    Boolean(defaultName) &&
    defaultName.length <= MAX_NAME_LENGTH &&
    !defaultName.includes("\0") &&
    defaultName === path.basename(defaultName) &&
    defaultName === path.win32.basename(defaultName) &&
    defaultName !== "." &&
    defaultName !== ".."
  );
}

/** Share cards and progress photos: well above a 1080x1350 PNG or a 12 MB photo. */
export const MAX_IMAGE_BYTES = 16 * 1024 * 1024;
const IMAGE_URL = /^data:image\/(png|jpeg);base64,([A-Za-z0-9+/]+={0,2})$/;

/** The bytes of an image data URL (PNG or JPEG only), or an error. */
export function imageBytes(dataUrl: unknown): { mime: "png" | "jpeg"; bytes: Buffer } {
  if (typeof dataUrl !== "string" || dataUrl.length > (MAX_IMAGE_BYTES * 4) / 3 + 64) throw new Error("invalid image");
  const m = IMAGE_URL.exec(dataUrl);
  if (!m) throw new Error("only PNG and JPEG images can be saved");
  const bytes = Buffer.from(m[2], "base64");
  if (!bytes.length || bytes.length > MAX_IMAGE_BYTES) throw new Error("invalid image");
  const png = bytes[0] === 0x89 && bytes[1] === 0x50;
  const jpeg = bytes[0] === 0xff && bytes[1] === 0xd8;
  if ((m[1] === "png" && !png) || (m[1] === "jpeg" && !jpeg)) throw new Error("the image data does not match its type");
  return { mime: m[1] as "png" | "jpeg", bytes };
}

/** image:save: a plain file name ending in the image's own extension, and a PNG/JPEG data URL. */
export function validateImageSave(req: unknown): ImageSaveRequest & { bytes: Buffer } {
  if (!req || typeof req !== "object") throw new Error("invalid image request");
  const { defaultName, dataUrl } = req as Record<string, unknown>;
  const { mime, bytes } = imageBytes(dataUrl);
  if (!plainName(defaultName)) throw new Error("invalid image file name");
  const ext = mime === "png" ? /\.png$/i : /\.jpe?g$/i;
  if (!ext.test(defaultName)) throw new Error("the file name must match the image type");
  return { defaultName, dataUrl: dataUrl as string, bytes };
}

/** The weekly recap video (v1.2): about 15 s of 720p WebM is a few MB; this is far above it. */
export const MAX_VIDEO_BYTES = 64 * 1024 * 1024;
const VIDEO_URL = /^data:video\/webm(?:;codecs=[a-z0-9.,]+)?;base64,([A-Za-z0-9+/]+={0,2})$/;

/** video:save: a plain file name ending in .webm and a WebM data URL (EBML magic bytes). */
export function validateVideoSave(req: unknown): VideoSaveRequest & { bytes: Buffer } {
  if (!req || typeof req !== "object") throw new Error("invalid video request");
  const { defaultName, dataUrl } = req as Record<string, unknown>;
  if (typeof dataUrl !== "string" || dataUrl.length > (MAX_VIDEO_BYTES * 4) / 3 + 64) throw new Error("invalid video");
  const m = VIDEO_URL.exec(dataUrl);
  if (!m) throw new Error("only WebM videos can be saved");
  const bytes = Buffer.from(m[1], "base64");
  if (!bytes.length || bytes.length > MAX_VIDEO_BYTES) throw new Error("invalid video");
  if (!(bytes[0] === 0x1a && bytes[1] === 0x45 && bytes[2] === 0xdf && bytes[3] === 0xa3)) throw new Error("the video data is not WebM");
  if (!plainName(defaultName)) throw new Error("invalid video file name");
  if (!/\.webm$/i.test(defaultName)) throw new Error("the file name must end in .webm");
  return { defaultName, dataUrl, bytes };
}

const MAX_CLIPBOARD_TEXT = 4000;

/** clipboard:write: up to 4000 characters of text and/or one PNG/JPEG image. */
export function validateClipboard(req: unknown): ClipboardWriteRequest {
  if (!req || typeof req !== "object") throw new Error("invalid clipboard request");
  const { text, imageDataUrl } = req as Record<string, unknown>;
  if (text === undefined && imageDataUrl === undefined) throw new Error("nothing to copy");
  if (text !== undefined && (typeof text !== "string" || text.length > MAX_CLIPBOARD_TEXT)) throw new Error("invalid text");
  if (imageDataUrl !== undefined) imageBytes(imageDataUrl);
  return { text: text as string | undefined, imageDataUrl: imageDataUrl as string | undefined };
}

/**
 * share:open: only X's own post composer, over https, with nothing but a `text` query.
 * Every other URL is refused, so the renderer cannot open arbitrary sites through it.
 */
const SHARE_HOSTS = new Set(["x.com", "twitter.com"]);
const SHARE_PATHS = new Set(["/intent/tweet", "/intent/post"]);

export function validateShareUrl(raw: unknown): string {
  if (typeof raw !== "string" || raw.length > 4000) throw new Error("invalid share link");
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    throw new Error("invalid share link");
  }
  if (url.protocol !== "https:" || !SHARE_HOSTS.has(url.hostname) || !SHARE_PATHS.has(url.pathname)) {
    throw new Error("that link is not an allowed share target");
  }
  if (url.username || url.password || url.port || url.hash) throw new Error("that link is not an allowed share target");
  for (const key of url.searchParams.keys()) {
    if (key !== "text") throw new Error("that link is not an allowed share target");
  }
  return url.toString();
}

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
