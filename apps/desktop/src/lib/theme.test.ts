import { describe, expect, it } from "vitest";

import { applyBackgroundArt, applyTheme, resolveTheme, toneOf } from "./theme";
import { themeArt } from "./themeArt";

describe("resolveTheme", () => {
  it("keeps an explicit choice", () => {
    expect(resolveTheme("dark", true)).toBe("dark");
    expect(resolveTheme("light", false)).toBe("light");
    expect(resolveTheme("frost", true)).toBe("frost");
  });

  it("follows the OS for system", () => {
    expect(resolveTheme("system", true)).toBe("light");
    expect(resolveTheme("system", false)).toBe("dark");
  });
});

describe("v1.2 themes", () => {
  it("are dark-toned, apart from the 1.1 Light look", () => {
    expect(toneOf("shadow")).toBe("dark");
    expect(toneOf("solar")).toBe("dark");
    expect(toneOf("light")).toBe("light");
  });

  it("apply the look, the tone and the background art setting to <html>", () => {
    const root = { dataset: {} } as unknown as HTMLElement;
    applyTheme("crimson", root);
    applyBackgroundArt("dim", root);
    expect(root.dataset).toMatchObject({ theme: "crimson", tone: "dark", art: "dim" });
  });

  it("find their art by file name; the 1.1 looks have none", () => {
    for (const t of ["shadow", "crimson", "frost", "emerald", "solar"] as const) {
      for (const k of ["landing", "bg", "event"] as const) expect(themeArt(t, k), `${t} ${k}`).toBeTruthy();
    }
    expect(themeArt("dark", "bg")).toBeNull();
    expect(themeArt("light", "landing")).toBeNull();
  });
});
