import type { IPC as SharedIPC } from "@ascend/shared";

/**
 * Runtime copy of the IPC channel names. `satisfies typeof SharedIPC` makes
 * tsc fail if this ever drifts from the contract in @ascend/shared, while
 * keeping the compiled main process free of any TypeScript-only imports.
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
} as const satisfies typeof SharedIPC;
