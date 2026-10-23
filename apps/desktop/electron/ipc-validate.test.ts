import { describe, expect, it } from "vitest";

import { MAX_EXPORT_BYTES, validateClipboard, validateExportSave, validateImageSave, validateShareUrl } from "./ipc-validate";

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

const PNG = `data:image/png;base64,${Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 1, 2, 3]).toString("base64")}`;
const JPEG = `data:image/jpeg;base64,${Buffer.from([0xff, 0xd8, 0xff, 0xe0, 1, 2, 3]).toString("base64")}`;

describe("validateImageSave (v1.1 share cards and photos)", () => {
  it("accepts a PNG or JPEG with a matching plain name", () => {
    expect(validateImageSave({ defaultName: "ascend-pr.png", dataUrl: PNG }).bytes[0]).toBe(0x89);
    expect(validateImageSave({ defaultName: "photo-2026-10-23.jpg", dataUrl: JPEG }).bytes[0]).toBe(0xff);
  });

  it.each([
    { defaultName: "card.png", dataUrl: "data:text/html;base64,PGgxPg==" },
    { defaultName: "card.png", dataUrl: JPEG },
    { defaultName: "card.exe", dataUrl: PNG },
    { defaultName: "../card.png", dataUrl: PNG },
    { defaultName: "card.png", dataUrl: PNG.replace("data:image/png", "data:image/jpeg") },
    { defaultName: "card.png" },
  ])("rejects %j", (req) => {
    expect(() => validateImageSave(req)).toThrow();
  });
});

describe("validateClipboard", () => {
  it("takes text, an image or both", () => {
    expect(validateClipboard({ text: "New PR #ASCEND" })).toEqual({ text: "New PR #ASCEND", imageDataUrl: undefined });
    expect(validateClipboard({ text: "x", imageDataUrl: PNG }).imageDataUrl).toBe(PNG);
  });

  it.each([{}, { text: 4 }, { text: "x".repeat(4001) }, { imageDataUrl: "data:image/gif;base64,R0lG" }])("rejects %j", (req) => {
    expect(() => validateClipboard(req)).toThrow();
  });
});

describe("validateShareUrl (allowlist)", () => {
  it("allows only X's post composer with a text query", () => {
    expect(validateShareUrl("https://x.com/intent/tweet?text=New%20PR")).toBe("https://x.com/intent/tweet?text=New%20PR");
    expect(validateShareUrl("https://twitter.com/intent/post?text=a")).toContain("twitter.com");
  });

  it.each([
    "http://x.com/intent/tweet?text=a",
    "https://x.com.evil.example/intent/tweet?text=a",
    "https://evil.example/?u=https://x.com/intent/tweet",
    "https://x.com/settings",
    "https://x.com/intent/tweet?text=a&url=https://evil.example",
    "https://user@x.com/intent/tweet?text=a",
    "file:///C:/Windows/system32/calc.exe",
    "javascript:alert(1)",
    42,
  ])("refuses %s", (url) => {
    expect(() => validateShareUrl(url)).toThrow();
  });
});
