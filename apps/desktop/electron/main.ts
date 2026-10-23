/**
 * Electron main process.
 *
 * Security defaults: contextIsolation + sandbox on, nodeIntegration off,
 * navigation and new windows blocked, and the renderer can only reach the
 * sidecar through the typed IPC channels in @ascend/shared (IPC).
 */
import { app, BrowserWindow, clipboard, ClipboardItem, dialog, ipcMain, nativeImage, powerSaveBlocker, shell } from "electron";
import fs from "node:fs";
import path from "node:path";

import type { SidecarRequest } from "@ascend/shared";

import { IPC } from "./channels";
import { validateClipboard, validateExportSave, validateImageSave, validateShareUrl } from "./ipc-validate";
import { SidecarManager } from "./sidecar";

app.setName("ASCEND");

const isDev = !app.isPackaged;
// The installed app keeps its data in %APPDATA%\ASCEND; an unpackaged dev run uses
// %APPDATA%\ASCEND-dev, so demo data seeded while developing never reaches the installed
// app (the 1.0.0 "pre-loaded data" bug). Set before anything reads userData.
if (isDev) app.setPath("userData", path.join(app.getPath("appData"), "ASCEND-dev"));
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
    if (!["GET", "POST", "PUT", "PATCH", "DELETE"].includes(req.method)) {
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

  ipcMain.handle(IPC.exportSave, async (_e, raw: unknown) => {
    const req = validateExportSave(raw); // throws: the renderer's promise rejects
    const result = await dialog.showSaveDialog({ defaultPath: req.defaultName });
    if (result.canceled || !result.filePath) return { saved: false, path: null };
    fs.writeFileSync(result.filePath, req.content, "utf8");
    return { saved: true, path: result.filePath };
  });

  ipcMain.handle(IPC.imageSave, async (_e, raw: unknown) => {
    const req = validateImageSave(raw);
    const ext = path.extname(req.defaultName).slice(1).toLowerCase();
    const result = await dialog.showSaveDialog({ defaultPath: req.defaultName, filters: [{ name: "Image", extensions: [ext] }] });
    if (result.canceled || !result.filePath) return { saved: false, path: null };
    fs.writeFileSync(result.filePath, req.bytes);
    return { saved: true, path: result.filePath };
  });

  ipcMain.handle(IPC.clipboardWrite, async (_e, raw: unknown) => {
    const req = validateClipboard(raw);
    const items: Record<string, string | Blob> = {};
    if (req.text !== undefined) items["text/plain"] = req.text;
    if (req.imageDataUrl) {
      const png = nativeImage.createFromDataURL(req.imageDataUrl).toPNG();
      items["image/png"] = new Blob([new Uint8Array(png)], { type: "image/png" });
    }
    await clipboard.write([new ClipboardItem(items)]);
    return true;
  });

  // Share cards: only X's post composer, nothing else (validateShareUrl is the allowlist).
  ipcMain.handle(IPC.shareOpen, async (_e, raw: unknown) => {
    await shell.openExternal(validateShareUrl(raw));
    return true;
  });

  // The full-screen timer keeps the screen awake (no dimming or sleep) until it ends.
  // One blocker at most; anything but a strict true releases it.
  ipcMain.handle(IPC.keepAwake, (_e, on: unknown) => {
    if (on === true) {
      if (awakeBlocker === null || !powerSaveBlocker.isStarted(awakeBlocker)) {
        awakeBlocker = powerSaveBlocker.start("prevent-display-sleep");
      }
      return true;
    }
    releaseAwake();
    return false;
  });

  ipcMain.handle(IPC.appInfo, () => ({
    version: app.getVersion(),
    platform: process.platform,
    electron: process.versions.electron,
  }));
}

let awakeBlocker: number | null = null;

function releaseAwake(): void {
  if (awakeBlocker !== null && powerSaveBlocker.isStarted(awakeBlocker)) powerSaveBlocker.stop(awakeBlocker);
  awakeBlocker = null;
}

// One running instance only: a second launch focuses the existing window.
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => BrowserWindow.getAllWindows()[0]?.focus());
  // Windows shows desktop notifications (the trainer's reminders) only for an app with an
  // AppUserModelID; it matches the installer's appId.
  if (process.platform === "win32") app.setAppUserModelId("app.ascend.desktop");

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

  app.on("window-all-closed", () => {
    releaseAwake();
    app.quit();
  });
  app.on("before-quit", (e) => {
    if (sidecar.getStatus().state === "stopped") return;
    e.preventDefault();
    void sidecar.stop().finally(() => app.exit(0));
  });
}
