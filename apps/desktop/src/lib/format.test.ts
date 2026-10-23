import { describe, expect, it } from "vitest";

import { count, dateLabel, dayLabel, kcal, num, pct, portionLabel, readyAtLabel, dateRange } from "./format";

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
    expect(dayLabel("2026-10-18", today)).toBe("Sun 18 Oct");
    expect(dateLabel("2026-10-20")).toBe("Tue 20 Oct");
  });
  it("says ready now without a time", () => {
    expect(readyAtLabel(null)).toBe("ready now");
  });
});

describe("num", () => {
  it("groups digits the same way everywhere (en-IN), so both sides of the XP bar match", () => {
    expect(num(12541)).toBe("12,541");
    expect(num(25974)).toBe("25,974");
    expect(num(382416)).toBe("3,82,416");
    expect(num(999.6)).toBe("1,000");
  });
});

describe("count", () => {
  it("uses the singular only for exactly one", () => {
    expect(count(1, "set")).toBe("1 set");
    expect(count(0, "set")).toBe("0 sets");
    expect(count(12, "rep")).toBe("12 reps");
    expect(count(1, "hard set")).toBe("1 hard set");
  });
});

describe("dateRange", () => {
  const today = new Date(2026, 9, 23);
  it("leaves the year out inside this year and adds it when either end is in another year", () => {
    expect(dateRange("2026-11-24", "2026-12-15", today)).toBe("24 Nov – 15 Dec");
    expect(dateRange("2027-11-24", "2028-08-15", today)).toBe("Nov 2027 – Aug 2028");
    expect(dateRange("2026-12-20", "2027-01-10", today)).toBe("Dec 2026 – Jan 2027");
  });
});
