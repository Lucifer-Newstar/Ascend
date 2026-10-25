import { describe, expect, it, vi } from "vitest";

import { validateDesktopHabits } from "./ipc-validate";
import { hideOnClose, loginItemSupported, trayMenu } from "./tray";

describe("tray menu", () => {
  it("opens, starts today's workout and quits", () => {
    const h = { show: vi.fn(), action: vi.fn(), quit: vi.fn() };
    const items = trayMenu(h);
    expect(items.map((i) => i.label ?? i.type)).toEqual(["Open ASCEND", "Start today's workout", "separator", "Quit ASCEND"]);
    items[1].click?.();
    expect(h.show).toHaveBeenCalledTimes(1);
    expect(h.action).toHaveBeenCalledWith("start-workout");
    items[0].click?.();
    expect(h.action).toHaveBeenLastCalledWith("open");
    items[3].click?.();
    expect(h.quit).toHaveBeenCalledTimes(1);
  });

  it("hides on close only while the tray is on and the app is not quitting", () => {
    expect(hideOnClose({ trayOn: true, quitting: false })).toBe(true);
    expect(hideOnClose({ trayOn: true, quitting: true })).toBe(false);
    expect(hideOnClose({ trayOn: false, quitting: false })).toBe(false);
  });

  it("offers start with Windows only where a login item exists", () => {
    expect(loginItemSupported("win32")).toBe(true);
    expect(loginItemSupported("linux")).toBe(false);
  });
});

describe("validateDesktopHabits", () => {
  it("accepts two strict booleans", () => {
    expect(validateDesktopHabits({ tray: true, openAtLogin: false })).toEqual({ tray: true, openAtLogin: false });
  });

  it.each([null, "on", {}, { tray: "true", openAtLogin: false }, { tray: true }, { tray: 1, openAtLogin: 0 }])("refuses %j", (raw) => {
    expect(() => validateDesktopHabits(raw)).toThrow("invalid desktop settings");
  });
});
