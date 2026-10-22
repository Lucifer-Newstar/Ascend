// @vitest-environment jsdom
import { describe, expect, it } from "vitest";

import { FileTooLargeError, readTextFile, todayStamp } from "./files";

describe("readTextFile", () => {
  it("returns the file text", async () => {
    const file = new File(["Date,Workout Name\n"], "strong.csv", { type: "text/csv" });
    await expect(readTextFile(file)).resolves.toBe("Date,Workout Name\n");
  });

  it("refuses files over the limit before reading them", async () => {
    const file = new File(["x".repeat(2048)], "big.csv");
    await expect(readTextFile(file, 1024)).rejects.toBeInstanceOf(FileTooLargeError);
    await expect(readTextFile(file, 1024)).rejects.toThrow(/limit is/);
  });
});

describe("todayStamp", () => {
  it("formats as YYYY-MM-DD", () => {
    expect(todayStamp(new Date(2026, 9, 20, 9, 30))).toBe("2026-10-20");
  });

  it("uses the local date, not UTC (an export at 00:30 in India is still today)", () => {
    const saved = process.env.TZ;
    process.env.TZ = "Asia/Kolkata"; // Node re-reads TZ when it changes
    try {
      // 00:30 IST on 21 Oct is 19:00 UTC on 20 Oct.
      expect(todayStamp(new Date("2026-10-20T19:00:00Z"))).toBe("2026-10-21");
    } finally {
      process.env.TZ = saved;
      if (saved === undefined) delete process.env.TZ;
    }
  });
});
