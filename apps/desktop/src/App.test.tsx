import { describe, expect, it } from "vitest";

import { pageFromHash } from "./App";

describe("pageFromHash", () => {
  it("maps known hashes to pages", () => {
    expect(pageFromHash("#data")).toBe("settings"); // 1.1 Import & export lives in Settings now
    expect(pageFromHash("#history")).toBe("history");
  });

  it("falls back to the dashboard", () => {
    expect(pageFromHash("")).toBe("dashboard");
    expect(pageFromHash("#nope")).toBe("dashboard");
  });
});
