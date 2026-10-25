import { describe, expect, it } from "vitest";

import { forgetShort, localDay, readShort, rememberShort } from "./shortSession";

const mem = () => {
  const m = new Map<string, string>();
  return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => void m.set(k, v), removeItem: (k: string) => void m.delete(k) };
};
const s = { session: "Push A", minutes: 9, items: [], note: "", algo_version: "schedule-v1" };

describe("short session memory", () => {
  it("keeps the short session for the local day only", () => {
    const store = mem();
    const day = new Date(2026, 9, 26, 23, 50);
    rememberShort(s, day, store);
    expect(readShort(new Date(2026, 9, 26, 23, 59), store)?.session).toBe("Push A");
    expect(readShort(new Date(2026, 9, 27, 0, 1), store)).toBeNull();
    forgetShort(store);
    expect(readShort(day, store)).toBeNull();
    expect(localDay(day)).toBe("2026-10-26");
  });
});
