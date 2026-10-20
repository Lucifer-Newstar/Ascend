import { describe, expect, it } from "vitest";

import { PAGE_KEYS, pageForKey } from "./shortcuts";

const key = (k: string, mods: Partial<{ ctrlKey: boolean; metaKey: boolean; altKey: boolean; shiftKey: boolean }> = {}) => ({
  key: k, ctrlKey: false, metaKey: false, altKey: false, shiftKey: false, ...mods,
});

describe("pageForKey", () => {
  it("maps Ctrl+1…9 and Ctrl+0 to the pages in sidebar order", () => {
    expect(pageForKey(key("1", { ctrlKey: true }))).toBe("dashboard");
    expect(pageForKey(key("3", { ctrlKey: true }))).toBe("library");
    expect(pageForKey(key("4", { ctrlKey: true }))).toBe("skills");
    expect(pageForKey(key("9", { ctrlKey: true }))).toBe("data");
    expect(pageForKey(key("0", { ctrlKey: true }))).toBe("settings");
    expect(PAGE_KEYS).toHaveLength(10);
  });

  it("accepts Cmd on macOS dev machines", () => {
    expect(pageForKey(key("2", { metaKey: true }))).toBe("workout");
  });

  it("ignores plain digits, other modifiers and out-of-range keys", () => {
    expect(pageForKey(key("1"))).toBeNull(); // typing a number in a field
    expect(pageForKey(key("1", { ctrlKey: true, shiftKey: true }))).toBeNull();
    expect(pageForKey(key("1", { ctrlKey: true, altKey: true }))).toBeNull();
    expect(pageForKey(key("F1", { ctrlKey: true }))).toBeNull();
    expect(pageForKey(key("k", { ctrlKey: true }))).toBeNull();
  });
});
