import http from "node:http";
import type { AddressInfo } from "node:net";

import { afterEach, describe, expect, it } from "vitest";

import { healthProof, recentCrashes, SidecarManager, sidecarEnv } from "./sidecar";

const parent = {
  PATH: "/usr/bin",
  APPDATA: "C:\\Users\\me\\AppData\\Roaming",
  ASCEND_TOKEN: "dev",
  ASCEND_HOST: "0.0.0.0",
  Ascend_Db_Url: "sqlite:///elsewhere.db",
  ASCEND_DEV: "1",
  ASCEND_PORT: "1",
  ASCEND_COACH_MODEL: "llama3.2:3b",
  ASCEND_OLLAMA_ALLOW_REMOTE: "1",
  NODE_OPTIONS: "--require evil.js",
  ELECTRON_RUN_AS_NODE: "1",
  PYTHONPATH: "C:\\evil",
  OLLAMA_HOST: "127.0.0.1:11434",
};

describe("sidecarEnv", () => {
  it("drops inherited ASCEND_* settings so the token, host and database can't be overridden", () => {
    const env = sidecarEnv(parent, { isPackaged: true, port: 50123, dataDir: "D:\\data" });
    expect(env.ASCEND_TOKEN).toBeUndefined();
    expect(env.ASCEND_HOST).toBeUndefined();
    expect(env.Ascend_Db_Url).toBeUndefined(); // Windows names are case-insensitive
    expect(env.ASCEND_DEV).toBeUndefined();
    expect(env.ASCEND_PORT).toBe("50123");
    expect(env.ASCEND_DATA_DIR).toBe("D:\\data");
    expect(env.ASCEND_COACH_MODEL).toBe("llama3.2:3b");
    expect(env.ASCEND_OLLAMA_ALLOW_REMOTE).toBe("1");
  });

  it("keeps the ordinary environment but not runtime-injection variables", () => {
    const env = sidecarEnv(parent, { isPackaged: true, port: 1, dataDir: "d" });
    expect(env.PATH).toBe("/usr/bin");
    expect(env.APPDATA).toBe(parent.APPDATA);
    expect(env.OLLAMA_HOST).toBe("127.0.0.1:11434");
    expect(env.NODE_OPTIONS).toBeUndefined();
    expect(env.ELECTRON_RUN_AS_NODE).toBeUndefined();
    expect(env.PYTHONPATH).toBeUndefined();
  });

  it("leaves PYTHON* alone in development, where uv runs a normal interpreter", () => {
    const env = sidecarEnv(parent, { isPackaged: false, port: 1, dataDir: "d" });
    expect(env.PYTHONPATH).toBe("C:\\evil");
    expect(env.ASCEND_TOKEN).toBeUndefined();
  });

  it("does not modify the parent environment", () => {
    const copy = { ...parent };
    sidecarEnv(parent, { isPackaged: true, port: 1, dataDir: "d" });
    expect(parent).toEqual(copy);
  });
});

const servers: http.Server[] = [];
afterEach(() => {
  for (const s of servers.splice(0)) s.close();
});

function serve(handler: http.RequestListener): Promise<number> {
  return new Promise((resolve) => {
    const srv = http.createServer(handler);
    servers.push(srv);
    srv.listen(0, "127.0.0.1", () => resolve((srv.address() as AddressInfo).port));
  });
}

function manager(port: number, extra: Partial<ConstructorParameters<typeof SidecarManager>[0]> = {}) {
  const m = new SidecarManager({
    isPackaged: true,
    resourcesPath: "/nowhere",
    devRoot: "/nowhere",
    dataDir: "/nowhere",
    log: () => {},
    ...extra,
  });
  const inner = m as unknown as { status: { state: string; port: number } };
  inner.status = { ...inner.status, state: "ready", port };
  return m;
}

describe("health proof (review L12)", () => {
  it("matches the sidecar's HMAC", () => {
    // Same value as app.core.security.health_proof("t0ken") in the sidecar.
    expect(healthProof("t0ken")).toBe("e46da2c50c29879fd2a148f6f6efc7722f4f310fb8100329b593c00f435b3036");
  });

  it("refuses a server on our port that cannot prove it knows the token", async () => {
    const seen: (string | undefined)[] = [];
    const port = await serve((req, res) => {
      seen.push(req.headers.authorization);
      res.setHeader("content-type", "application/json");
      res.end(JSON.stringify({ status: "ok" }));
    });
    const m = manager(port, { healthTimeoutMs: 2000 });
    const wait = (m as unknown as { waitHealthy(): Promise<void> }).waitHealthy();
    await expect(wait).rejects.toThrow(/another process/);
    expect(seen.every((h) => h === undefined)).toBe(true);
  });

  it("accepts our sidecar", async () => {
    let token = "";
    const port = await serve((_req, res) => {
      res.setHeader("content-type", "application/json");
      res.end(JSON.stringify({ status: "ok", proof: healthProof(token) }));
    });
    const m = manager(port, { healthTimeoutMs: 2000 });
    token = m.token;
    await (m as unknown as { waitHealthy(): Promise<void> }).waitHealthy();
  });
});

describe("request timeout (review L10)", () => {
  it("fails a request the sidecar never answers", async () => {
    const port = await serve(() => {
      /* never respond */
    });
    const m = manager(port, { requestTimeoutMs: 200 });
    const started = Date.now();
    await expect(m.request("GET", "/profile")).rejects.toThrow();
    expect(Date.now() - started).toBeLessThan(2000);
  });

  it("does not proxy the endless /events stream", async () => {
    const m = manager(1);
    await expect(m.request("GET", "/events")).rejects.toThrow(/events/);
  });
});

describe("restart budget (review L9)", () => {
  it("forgets crashes outside the window", () => {
    const hour = 3_600_000;
    expect(recentCrashes([0, hour, 2 * hour], 2 * hour + 1000, 10 * 60_000)).toEqual([2 * hour]);
    expect(recentCrashes([1000, 2000, 3000], 4000, 10 * 60_000)).toHaveLength(3);
  });
});
