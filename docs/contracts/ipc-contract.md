# IPC Contract — `window.ascend` (preload ↔ main)

> The only API the renderer has. Types live in `packages/shared/src/ipc.ts`; the bridge
> is `apps/desktop/electron/preload.ts`; handlers are in `apps/desktop/electron/main.ts`;
> the runtime channel list is `apps/desktop/electron/channels.ts` (it `satisfies` the
> shared type, so a renamed channel fails type-checking).
> Owner: Dhanush; reviewer: Navin. Register: [port-register.md §4](../architecture/port-register.md#4-ipc-channels-renderer--main).
>
> **Version 1.** The four `implemented` channels match the v0.1 code skeleton
> (2026-10-20). `planned` channels are the agreed v1.0 additions; they are additive —
> existing names and shapes do not change.

---

## 1. Rules

1. The renderer never sees `ipcRenderer`, Node, the launch token or the sidecar port
   (`contextIsolation: true`, `sandbox: true`, `nodeIntegration: false`).
2. Every channel name comes from the `IPC` constant; main registers handlers only for
   those names (the allow-list).
3. Payloads are validated in main before use (today: hand-written guards; Phase 1:
   **zod** schemas generated next to the shared types).
4. Renderer → main calls are `invoke` (Promise). Main → renderer pushes use
   `webContents.send` and reach callbacks registered through the bridge; each `on…`
   function returns an unsubscribe function.
5. Errors reject the Promise with an `IpcError` (§4), never a raw stack.
6. Files cross as paths chosen in native dialogs or as text content, never as handles.

## 2. Implemented in v0.1 (matches the code)

```ts
// packages/shared/src/ipc.ts (v0.1)
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
} as const;

export type HttpMethod = "GET" | "POST" | "PUT" | "DELETE";

export interface SidecarRequest { method: HttpMethod; path: string; body?: unknown; }  // path starts with "/"
export interface SidecarResponse<T = unknown> { status: number; ok: boolean; data: T; }

export type SidecarState = "starting" | "ready" | "restarting" | "failed" | "stopped";
export interface SidecarStatus { state: SidecarState; port: number | null; restarts: number; lastError: string | null; }

export interface ExportSaveRequest { defaultName: string; content: string; }
export interface ExportSaveResult { saved: boolean; path: string | null; }

export interface AppInfo { version: string; platform: string; electron: string; }

export interface AscendBridge {
  request<T = unknown>(req: SidecarRequest): Promise<SidecarResponse<T>>;
  sidecarStatus(): Promise<SidecarStatus>;
  saveExport(req: ExportSaveRequest): Promise<ExportSaveResult>;
  appInfo(): Promise<AppInfo>;
}
```

| Bridge function | Channel | Kind | Request | Response | Status |
|---|---|---|---|---|---|
| `request` | `sidecar:request` | invoke | `SidecarRequest` — main adds `Authorization: Bearer <token>` and forwards to `http://127.0.0.1:<port><path>` | `SidecarResponse` | implemented |
| `sidecarStatus` | `sidecar:status` | invoke | none | `SidecarStatus` | implemented |
| `saveExport` | `export:save` | invoke | `ExportSaveRequest` (native save dialog, then main writes `content`) | `ExportSaveResult` | implemented |
| `appInfo` | `app:info` | invoke | none | `AppInfo` | implemented |
| `saveImage` | `image:save` | invoke | `ImageSaveRequest`: a plain file name with the image's own extension and a PNG/JPEG data URL (≤ 16 MB, magic bytes checked); native save dialog | `ExportSaveResult` | implemented (v1.1) |
| `copyToClipboard` | `clipboard:write` | invoke | `ClipboardWriteRequest`: text ≤ 4000 chars and/or one PNG/JPEG data URL | `true` | implemented (v1.1) |
| `openShareLink` | `share:open` | invoke | a URL; only `https://x.com` or `https://twitter.com` `/intent/tweet` or `/intent/post` with a single `text` query passes (`validateShareUrl`) | `true` | implemented (v1.1) |
| `keepAwake` | `power:keep-awake` | invoke | `true` keeps the display awake for the full-screen timer, `false` lets it sleep again | `boolean` (kept awake now) | implemented (v1.2) |
| `saveVideo` | `video:save` | invoke | `VideoSaveRequest`: a plain file name ending in `.webm` and a WebM data URL (≤ 64 MB, EBML magic bytes checked); native save dialog. Used for the weekly recap video | `ExportSaveResult` | implemented (v1.2) |

## 3. Planned for v1.0 (additive)

```ts
// additions to IPC and AscendBridge (v1.0)
export const IPC_V1_ADDITIONS = {
  eventsSubscribe: "events:subscribe",
  eventsUnsubscribe: "events:unsubscribe",
  eventsPush: "events:push",              // main → renderer
  sidecarStateChanged: "sidecar:state-changed", // main → renderer
  sidecarRestart: "sidecar:restart",
  openPath: "app:open-path",
  pickImage: "files:pick-image",
  pickImport: "files:pick-import",
  notifyShow: "notify:show",
  notifySchedule: "notify:schedule",
  updateCheck: "update:check",
  updateStatus: "update:status",          // main → renderer
  updateInstall: "update:install",
  titlebarTheme: "window:titlebar-theme",
} as const;

export interface ServerEvent { event: string; id: string; data: unknown; }

export interface AscendBridgeV1 extends AscendBridge {
  subscribe(types: string[], cb: (e: ServerEvent) => void): Promise<() => void>;
  onSidecarState(cb: (s: SidecarStatus) => void): () => void;
  restartSidecar(): Promise<SidecarStatus>;
  openPath(target: "logs" | "data" | "backups" | "crashes"): Promise<void>;
  pickImage(): Promise<string | null>;
  pickImport(kind: "csv" | "ascendbak"): Promise<string | null>;
  notify(n: { title: string; body: string; tag?: string }): Promise<void>;
  scheduleNotification(n: { id: string; at: string; title: string; body: string }): Promise<void>;
  checkUpdate(): Promise<{ available: boolean; version?: string }>;
  onUpdateStatus(cb: (s: { state: "available" | "downloading" | "ready" | "error"; progress?: number }) => void): () => void;
  installUpdate(): Promise<void>;
  setTitlebarTheme(theme: "dark" | "light"): Promise<void>;
}
```

| Bridge function | Channel | Kind | Request | Response | Errors | Phase |
|---|---|---|---|---|---|---|
| `subscribe` | `events:subscribe` → `events:push` | invoke + push | event names from [port-register.md §5](../architecture/port-register.md#5-sse-event-names-sidecar--main--renderer) | unsubscribe fn; `ServerEvent` pushes | `IPC_INVALID_PAYLOAD` | 1 |
| `onSidecarState` | `sidecar:state-changed` | push | — | `SidecarStatus` | — | 0 |
| `restartSidecar` | `sidecar:restart` | invoke | none | `SidecarStatus` | `SIDECAR_RESTART_LIMIT` | 0 |
| `openPath` | `app:open-path` | invoke | enum target | void | `IPC_INVALID_PAYLOAD` | 3 |
| `pickImage` | `files:pick-image` | invoke | none | path or null | — | 2 |
| `pickImport` | `files:pick-import` | invoke | `kind` | path or null | — | 3 |
| `notify` | `notify:show` | invoke | title ≤ 64, body ≤ 200 chars | void | `NOTIFY_QUIET_HOURS` | 1 |
| `scheduleNotification` | `notify:schedule` | invoke | id, ISO time, title, body | void | `NOTIFY_TRAY_DISABLED` | 1 |
| `checkUpdate` | `update:check` | invoke | none | availability | `UPDATE_OFFLINE`, `UPDATE_DISABLED` | 3 |
| `onUpdateStatus` | `update:status` | push | — | status | — | 3 |
| `installUpdate` | `update:install` | invoke | none | (app quits) | `UPDATE_NOT_READY` | 3 |
| `setTitlebarTheme` | `window:titlebar-theme` | invoke | `dark`/`light` | void | — | 4 |

`secure:get-key` (safeStorage key for v1.1 encryption) exists in **main only** and is
never exposed through the bridge.

## 4. Errors

```ts
export interface IpcError {
  code:
    | "IPC_CHANNEL_DENIED" | "IPC_INVALID_PAYLOAD"
    | "SIDECAR_UNAVAILABLE" | "SIDECAR_RESTART_LIMIT"
    | "NOTIFY_QUIET_HOURS" | "NOTIFY_TRAY_DISABLED"
    | "UPDATE_OFFLINE" | "UPDATE_DISABLED" | "UPDATE_NOT_READY";
  message: string;   // plain language, safe to show
  corrId?: string;   // matches log lines in main and sidecar (Phase 1)
}
```

HTTP errors from the sidecar are **not** IPC errors: `request` resolves with
`ok: false` and the sidecar's `{"detail": …}` in `data`. In v0.1, a request while the
sidecar is not `ready` rejects with the message `sidecar is <state>`; Phase 1 maps it to
`SIDECAR_UNAVAILABLE`.

## 5. Example

```ts
// renderer: log a set in workout 412
const res = await window.ascend.request<LoggedSet>({
  method: "POST",
  path: "/workouts/412/sets",
  body: { exercise_id: 17, weight_kg: 70, reps: 8, rpe: 8 },
});
if (res.ok) {
  // res.status === 201; res.data.set, res.data.xp_awarded, res.data.previous_best_e1rm
}
```

## 6. Tests

- **Type test:** `channels.ts` `satisfies typeof IPC` (already in v0.1).
- **Contract test (Vitest, Phase 1):** every bridge function maps to a channel in the
  register; every validator rejects unknown fields.
- **E2E (Playwright for Electron, Phase 3):** the page cannot reach `require`, `process`
  or `ipcRenderer`; `request` with a path that does not start with `/` is rejected.
