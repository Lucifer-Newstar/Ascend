import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { localDay, localDaysAgo } from "./localDate";

describe("local dates (v1.4)", () => {
  const tz = process.env.TZ;
  beforeAll(() => {
    process.env.TZ = "Asia/Kolkata"; // UTC+5:30, where the UTC bug showed
  });
  afterAll(() => {
    process.env.TZ = tz;
  });

  it("uses the local day, not the UTC one, just after midnight", () => {
    const early = new Date(2026, 9, 26, 1, 0); // 26 Oct 01:00 in India = 25 Oct 19:30 UTC
    expect(early.toISOString().slice(0, 10)).toBe("2026-10-25");
    expect(localDay(early)).toBe("2026-10-26");
  });

  it("counts days back on the calendar", () => {
    const now = new Date(2026, 9, 26, 0, 30);
    expect(localDaysAgo(7, now)).toBe("2026-10-19");
    expect(localDaysAgo(0, now)).toBe("2026-10-26");
    expect(localDaysAgo(1, new Date(2026, 2, 1, 0, 5))).toBe("2026-02-28");
  });
});

/** Rule check: no UTC date strings anywhere in the app's own code. */
function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) return sources(p);
    return /\.(ts|tsx)$/.test(name) && !/\.test\.tsx?$/.test(name) ? [p] : [];
  });
}

describe("rule: local system date/time", () => {
  it("never builds a date from toISOString()", () => {
    const root = join(__dirname, "..");
    const bad = sources(root).filter((f) => /toISOString\(\)\s*\.(slice\(0,\s*10\)|split\(["']T["']\))/.test(readFileSync(f, "utf8")));
    expect(bad).toEqual([]);
  });
});
