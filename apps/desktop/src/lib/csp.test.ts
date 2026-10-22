import fs from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { devCsp, widenConnectSrc } from "./csp";

const indexHtml = fs.readFileSync(path.resolve(__dirname, "../../index.html"), "utf8");

function connectSrc(html: string): string {
  const m = /content="[^"]*connect-src\s+([^;"]*)/.exec(html);
  if (!m) throw new Error("no connect-src");
  return m[1].trim();
}

describe("CSP", () => {
  it("ships connect-src 'self' only (review M3)", () => {
    expect(connectSrc(indexHtml)).toBe("'self'");
    expect(indexHtml).not.toMatch(/localhost|127\.0\.0\.1/);
  });

  it("widens connect-src for the dev server only", () => {
    const dev = widenConnectSrc(indexHtml);
    expect(connectSrc(dev)).toBe("'self' http://127.0.0.1:* http://localhost:* ws://127.0.0.1:* ws://localhost:*");
    // The other directives are untouched.
    const strip = (h: string) => h.replace(/connect-src [^"]*"/, "");
    expect(strip(dev)).toBe(strip(indexHtml));
  });

  it("is a serve-only Vite plugin, so `vite build` keeps the strict policy", () => {
    expect(devCsp().apply).toBe("serve");
  });
});
