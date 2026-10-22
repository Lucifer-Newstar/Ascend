import { describe, expect, it } from "vitest";

import { MAX_EXPORT_BYTES, validateExportSave } from "./ipc-validate";

describe("validateExportSave", () => {
  it("accepts a plain name and text", () => {
    expect(validateExportSave({ defaultName: "ascend-2026-10-22.json", content: "{}" })).toEqual({
      defaultName: "ascend-2026-10-22.json",
      content: "{}",
    });
  });

  it.each([
    null,
    "x",
    { defaultName: "a.json" },
    { defaultName: "a.json", content: 42 },
    { defaultName: "a.json", content: { toString: () => "x" } },
    { defaultName: "", content: "x" },
    { defaultName: "../../evil.bat", content: "x" },
    { defaultName: "C:\\Users\\me\\Startup\\evil.bat", content: "x" },
    { defaultName: "dir/evil.json", content: "x" },
    { defaultName: "a\u0000.json", content: "x" },
    { defaultName: "..", content: "x" },
    { defaultName: "x".repeat(121), content: "x" },
  ])("rejects %j", (req) => {
    expect(() => validateExportSave(req)).toThrow();
  });

  it("rejects payloads over the size cap", () => {
    expect(() => validateExportSave({ defaultName: "a.csv", content: "x".repeat(MAX_EXPORT_BYTES + 1) })).toThrow(
      /too large/,
    );
  });
});
