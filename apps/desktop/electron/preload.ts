/**
 * Preload: the only bridge between the sandboxed renderer and Electron main.
 * Exposes `window.ascend` (typed as AscendBridge) and nothing else; raw
 * ipcRenderer is never handed to the page.
 *
 * Channel names are inlined because a sandboxed preload can only
 * require("electron"), not local modules.
 */
import { contextBridge, ipcRenderer } from "electron";

import type { AscendBridge, IPC as SharedIPC } from "@ascend/shared";

// Typed against the shared contract, so a renamed channel fails type-checking.
const IPC: typeof SharedIPC = {
  sidecarRequest: "sidecar:request",
  sidecarStatus: "sidecar:status",
  exportSave: "export:save",
  appInfo: "app:info",
};

const bridge: AscendBridge = {
  request: (req) => ipcRenderer.invoke(IPC.sidecarRequest, req),
  sidecarStatus: () => ipcRenderer.invoke(IPC.sidecarStatus),
  saveExport: (req) => ipcRenderer.invoke(IPC.exportSave, req),
  appInfo: () => ipcRenderer.invoke(IPC.appInfo),
};

contextBridge.exposeInMainWorld("ascend", bridge);
