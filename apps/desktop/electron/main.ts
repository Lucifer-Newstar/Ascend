/**
 * Electron main process.
 *
 * Security defaults: contextIsolation + sandbox on, nodeIntegration off,
 * navigation and new windows blocked, and the renderer can only reach the
 * sidecar through the typed IPC channels in @ascend/shared (IPC).
 */
import { app, BrowserWindow, dialog, ipcMain, shell } from "electron";
import fs from "node:fs";
import path from "node:path";

import type { ExportSaveRequest, SidecarRequest } from "@ascend/shared";

import { IPC } from "./channels";
import { SidecarManager } from "./sidecar";

// Same user-data folder (%APPDATA%\ASCEND) in dev and when installed.
app.setName("ASCEND");

const isDev = !app.isPackaged;
const logFile = path.join(app.getPath("userData"), "logs", "main.log");

function log(line: string): void {
  // Local-only log file: nothing is ever sent off the machine.
  fs.mkdirSync(path.dirname(logFile), { recursive: true });
  fs.appendFileSync(logFile, `${new Date().toISOString()} ${line}\n`);
  if (isDev) console.log(line);
}

const sidecar = new SidecarManager({
  isPackaged: app.isPackaged,
  resourcesPath: process.resourcesPath,
  devRoot: path.resolve(__dirname, "..", "..", ".."),
  dataDir: path.join(app.getPath("userData"), "data"),
  log,
});

function createWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    backgroundColor: "#0A0E15",
    title: "ASCEND",
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
    },
  });

  // Block in-app navigation and open external links in the default browser.
  win.webContents.on("will-navigate", (e) => e.preventDefault());
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("https://")) void shell.openExternal(url);
    return { action: "deny" };
  });

  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (isDev && devUrl) void win.loadURL(devUrl);
  else void win.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  return win;
}

function registerIpc(): void {
  ipcMain.handle(IPC.sidecarRequest, async (_e, req: SidecarRequest) => {
    // Validate the shape: the renderer is treated as untrusted input.
    if (!req || typeof req.path !== "string" || !req.path.startsWith("/")) {
      return { status: 400, ok: false, data: { detail: "invalid request" } };
    }
    if (!["GET", "POST", "PUT", "DELETE"].includes(req.method)) {
      return { status: 405, ok: false, data: { detail: "method not allowed" } };
    }
    try {
      const { status, data } = await sidecar.request(req.method, req.path, req.body);
      return { status, ok: status >= 200 && status < 300, data };
    } catch (err) {
      return { status: 503, ok: false, data: { detail: (err as Error).message } };
    }
  });

  ipcMain.handle(IPC.sidecarStatus, () => sidecar.getStatus());

  ipcMain.handle(IPC.exportSave, async (_e, req: ExportSaveRequest) => {
    const result = await dialog.showSaveDialog({ defaultPath: req.defaultName });
    if (result.canceled || !result.filePath) return { saved: false, path: null };
    fs.writeFileSync(result.filePath, req.content, "utf8");
    return { saved: true, path: result.filePath };
  });

  ipcMain.handle(IPC.appInfo, () => ({
    version: app.getVersion(),
    platform: process.platform,
    electron: process.versions.electron,
  }));
}

// One running instance only: a second launch focuses the existing window.
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => BrowserWindow.getAllWindows()[0]?.focus());

  app.whenReady().then(async () => {
    registerIpc();
    createWindow(); // the renderer polls sidecarStatus until the engine is ready
    try {
      await sidecar.start();
      log("sidecar ready");
    } catch (err) {
      log(`sidecar failed to start: ${(err as Error).message}`);
      dialog.showErrorBox("ASCEND", `The local engine failed to start.\n${(err as Error).message}\n\nLog: ${logFile}`);
    }
  });

  app.on("window-all-closed", () => app.quit());
  app.on("before-quit", (e) => {
    if (sidecar.getStatus().state === "stopped") return;
    e.preventDefault();
    void sidecar.stop().finally(() => app.exit(0));
  });
}
