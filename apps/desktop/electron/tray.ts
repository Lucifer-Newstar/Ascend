/**
 * The opt-in tray icon (v1.4, review 2.2). Kept free of Electron imports so the menu and
 * the close rule are unit-tested; main.ts turns the template into a real Menu.
 *
 * With the tray on, closing the window only hides it: the renderer keeps running, so the
 * trainer's reminders (at most two a day, none on a rest day) still arrive. "Quit ASCEND"
 * in the tray menu really quits.
 */
import type { TrayAction } from "@ascend/shared";

export interface TrayItem {
  label?: string;
  type?: "separator";
  click?: () => void;
}

export interface TrayHandlers {
  show: () => void;
  action: (a: TrayAction) => void;
  quit: () => void;
}

export const TRAY_TOOLTIP = "ASCEND";

export function trayMenu(h: TrayHandlers): TrayItem[] {
  return [
    { label: "Open ASCEND", click: () => { h.show(); h.action("open"); } },
    { label: "Start today's workout", click: () => { h.show(); h.action("start-workout"); } },
    { type: "separator" },
    { label: "Quit ASCEND", click: h.quit },
  ];
}

/** Closing the window hides it to the tray only while the tray is on and we are not quitting. */
export function hideOnClose({ trayOn, quitting }: { trayOn: boolean; quitting: boolean }): boolean {
  return trayOn && !quitting;
}

/** Start with Windows is only offered where Electron supports a login item. */
export function loginItemSupported(platform: NodeJS.Platform): boolean {
  return platform === "win32" || platform === "darwin";
}
