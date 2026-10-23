/**
 * Typed IPC contract between the renderer (React) and Electron main.
 *
 * The renderer never gets Node access (contextIsolation: true, sandbox: true).
 * Preload exposes exactly the `AscendBridge` object below as `window.ascend`,
 * and every channel name used by main and preload comes from `IPC`.
 */

export const IPC = {
  sidecarRequest: "sidecar:request",
  sidecarStatus: "sidecar:status",
  exportSave: "export:save",
  appInfo: "app:info",
  imageSave: "image:save",
  clipboardWrite: "clipboard:write",
  shareOpen: "share:open",
} as const;

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface SidecarRequest {
  method: HttpMethod;
  /** Path on the sidecar, e.g. "/dashboard". Must start with "/". */
  path: string;
  body?: unknown;
}

export interface SidecarResponse<T = unknown> {
  status: number;
  ok: boolean;
  data: T;
}

export type SidecarState = "starting" | "ready" | "restarting" | "failed" | "stopped";

export interface SidecarStatus {
  state: SidecarState;
  port: number | null;
  restarts: number;
  lastError: string | null;
}

export interface ExportSaveRequest {
  defaultName: string;
  content: string;
}

export interface ExportSaveResult {
  saved: boolean;
  path: string | null;
}

/** image:save (v1.1): a PNG/JPEG data URL written where the user picks in the save dialog. */
export interface ImageSaveRequest {
  defaultName: string;
  dataUrl: string;
}

/** clipboard:write (v1.1): a caption and/or an image for share cards. */
export interface ClipboardWriteRequest {
  text?: string;
  imageDataUrl?: string;
}

export interface AppInfo {
  version: string;
  platform: string;
  electron: string;
}

/** The only API the renderer can see: `window.ascend`. */
export interface AscendBridge {
  request<T = unknown>(req: SidecarRequest): Promise<SidecarResponse<T>>;
  sidecarStatus(): Promise<SidecarStatus>;
  saveExport(req: ExportSaveRequest): Promise<ExportSaveResult>;
  appInfo(): Promise<AppInfo>;
  /** Save a share card or a progress photo through the save dialog. */
  saveImage(req: ImageSaveRequest): Promise<ExportSaveResult>;
  /** Put a caption and/or an image on the clipboard. */
  copyToClipboard(req: ClipboardWriteRequest): Promise<boolean>;
  /** Open an allowlisted share link (X's post composer) in the default browser. */
  openShareLink(url: string): Promise<boolean>;
}
