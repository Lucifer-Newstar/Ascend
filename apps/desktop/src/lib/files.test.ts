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
    expect(todayStamp(new Date("2026-10-20T09:30:00Z"))).toBe("2026-10-20");
  });
});
