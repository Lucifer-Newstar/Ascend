import { describe, expect, it } from "vitest";

import { dayLabel, kcal, pct, portionLabel, readyAtLabel } from "./format";

describe("pct", () => {
  it("clamps to 0..1", () => {
    expect(pct(50, 100)).toBe(0.5);
    expect(pct(150, 100)).toBe(1);
    expect(pct(-5, 100)).toBe(0);
  });
  it("handles a zero target", () => {
    expect(pct(10, 0)).toBe(0);
  });
});

describe("labels", () => {
  it("formats kcal with Indian grouping", () => {
    expect(kcal(2650.4)).toBe("2,650");
  });
  it("formats portions", () => {
    expect(portionLabel(1, "1 katori")).toBe("1 katori");
    expect(portionLabel(1.5, "1 katori")).toBe("1.5 × 1 katori");
  });
  it("labels today and yesterday", () => {
    const today = new Date(2026, 9, 20);
    expect(dayLabel("2026-10-20", today)).toBe("Today");
    expect(dayLabel("2026-10-19", today)).toBe("Yesterday");
  });
  it("says ready now without a time", () => {
    expect(readyAtLabel(null)).toBe("ready now");
  });
});
