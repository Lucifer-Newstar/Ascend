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
  keepAwake: "power:keep-awake",
  videoSave: "video:save",
  /** v1.4: renderer -> main, the opt-in tray icon and start-with-Windows switches. */
  desktopHabits: "desktop:habits",
  /** v1.4: main -> renderer, a tray menu pick ("open" or "start-workout"). */
  trayAction: "tray:action",
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

/** video:save (v1.2): the weekly recap video, a WebM data URL, behind a native save dialog. */
export interface VideoSaveRequest {
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

/**
 * desktop:habits (v1.4, review 2.2): both off by default. With the tray on, closing the
 * window keeps ASCEND in the tray so the trainer's reminders still arrive; openAtLogin
 * registers ASCEND to start with Windows.
 */
export interface DesktopHabits {
  tray: boolean;
  openAtLogin: boolean;
}

/** What the tray menu asks the renderer to do. */
export type TrayAction = "open" | "start-workout";

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
  /**
   * Keep the screen awake (true) or let it sleep again (false), for the full-screen
   * timer. Resolves to whether the screen is being kept awake now.
   */
  keepAwake(on: boolean): Promise<boolean>;
  /** Save the weekly recap video (WebM) through a native save dialog (v1.2). */
  saveVideo(req: VideoSaveRequest): Promise<ExportSaveResult>;
  /** Apply the tray and start-with-Windows switches (v1.4). Resolves to what main applied. */
  setDesktopHabits?(req: DesktopHabits): Promise<DesktopHabits>;
  /** Listen for tray menu picks (v1.4). Returns the function that stops listening. */
  onTrayAction?(cb: (action: TrayAction) => void): () => void;
}
