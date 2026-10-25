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
  imageSave: "image:save",
  clipboardWrite: "clipboard:write",
  shareOpen: "share:open",
  keepAwake: "power:keep-awake",
  videoSave: "video:save",
  desktopHabits: "desktop:habits",
  trayAction: "tray:action",
};

const bridge: AscendBridge = {
  request: (req) => ipcRenderer.invoke(IPC.sidecarRequest, req),
  sidecarStatus: () => ipcRenderer.invoke(IPC.sidecarStatus),
  saveExport: (req) => ipcRenderer.invoke(IPC.exportSave, req),
  appInfo: () => ipcRenderer.invoke(IPC.appInfo),
  saveImage: (req) => ipcRenderer.invoke(IPC.imageSave, req),
  copyToClipboard: (req) => ipcRenderer.invoke(IPC.clipboardWrite, req),
  openShareLink: (url) => ipcRenderer.invoke(IPC.shareOpen, url),
  keepAwake: (on) => ipcRenderer.invoke(IPC.keepAwake, on),
  saveVideo: (req) => ipcRenderer.invoke(IPC.videoSave, req),
  setDesktopHabits: (req) => ipcRenderer.invoke(IPC.desktopHabits, req),
  // Only the two known tray picks reach the page; the listener is removed on unsubscribe.
  onTrayAction: (cb) => {
    const listener = (_e: unknown, action: unknown) => {
      if (action === "open" || action === "start-workout") cb(action);
    };
    ipcRenderer.on(IPC.trayAction, listener);
    return () => {
      ipcRenderer.removeListener(IPC.trayAction, listener);
    };
  },
};

contextBridge.exposeInMainWorld("ascend", bridge);
