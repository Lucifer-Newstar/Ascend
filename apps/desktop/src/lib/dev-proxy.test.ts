import { describe, expect, it } from "vitest";

import { sidecarProxy } from "./dev-proxy";

describe("sidecarProxy", () => {
  it("forwards /api/* to the sidecar path with a localhost Host header", () => {
    const rule = sidecarProxy("http://sidecar:8765")["/api"];
    expect(rule.target).toBe("http://sidecar:8765");
    expect(rule.rewrite("/api/workouts?limit=5")).toBe("/workouts?limit=5");
    expect(rule.rewrite("/api")).toBe("/");
    expect(rule.headers.host).toBe("127.0.0.1");
  });

  it("defaults to the --dev sidecar", () => {
    const saved = process.env.ASCEND_SIDECAR_PROXY;
    delete process.env.ASCEND_SIDECAR_PROXY;
    try {
      expect(sidecarProxy()["/api"].target).toBe("http://127.0.0.1:8765");
    } finally {
      if (saved !== undefined) process.env.ASCEND_SIDECAR_PROXY = saved;
    }
  });
});
