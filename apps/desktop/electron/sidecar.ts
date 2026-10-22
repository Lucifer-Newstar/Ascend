/**
 * Sidecar lifecycle: spawn the Python API, wait until healthy, restart on crash.
 *
 *  1. pick a free localhost port (bind :0, read the port, close)
 *  2. generate a random 256-bit token for this launch
 *  3. spawn the sidecar: dev = `uv run python -m app` in services/sidecar,
 *     packaged = resources/sidecar/ascend-sidecar(.exe) built by PyInstaller
 *  4. write the token on its stdin (never in argv/env, so it isn't visible in
 *     the process list). The child gets a cleaned environment (sidecarEnv): no
 *     inherited ASCEND_* variable can replace the token, the bind address or the
 *     database (a leftover ASCEND_TOKEN=dev or ASCEND_HOST=0.0.0.0, for example)
 *  5. poll GET /health until 200 (timeout 30 s) and check its `proof` (an HMAC under
 *     the token): the token is only ever sent to a server that already knows it, not to
 *     a process that grabbed the port between steps 1 and 3
 *  6. on unexpected exit: restart with backoff, up to MAX_RESTARTS crashes in
 *     RESTART_WINDOW_MS (a sidecar that ran fine for hours gets a fresh budget)
 */
import { ChildProcess, spawn } from "node:child_process";
import { createHmac, randomBytes } from "node:crypto";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";

import type { SidecarStatus } from "@ascend/shared";

const HEALTH_TIMEOUT_MS = 30_000;
const HEALTH_POLL_TIMEOUT_MS = 2_000;
/** A renderer request that has not answered by then fails instead of hanging the IPC call. */
const REQUEST_TIMEOUT_MS = 30_000;
const MAX_RESTARTS = 3;
const RESTART_WINDOW_MS = 10 * 60_000;

export interface SidecarOptions {
  isPackaged: boolean;
  resourcesPath: string;
  /** Repo root in development (apps/desktop/../..). */
  devRoot: string;
  dataDir: string;
  log: (line: string) => void;
  /** Overrides for tests. */
  requestTimeoutMs?: number;
  healthTimeoutMs?: number;
}

/** What /health returns as `proof`: HMAC-SHA256 of a fixed label under the token. */
export function healthProof(token: string): string {
  return createHmac("sha256", token).update("ascend-sidecar-health").digest("hex");
}

/** Crash times still inside the restart window. */
export function recentCrashes(times: number[], now: number, windowMs = RESTART_WINDOW_MS): number[] {
  return times.filter((t) => now - t < windowMs);
}

/**
 * ASCEND_* settings a user may still set for the desktop app: the coach model, and the
 * explicit opt-in to a non-local Ollama (the sidecar refuses one without it).
 * Everything else under ASCEND_ (token, host, port, database, dev mode, data dir) comes
 * from Electron or not at all.
 */
const PASS_THROUGH = new Set(["ASCEND_COACH_MODEL", "ASCEND_OLLAMA_ALLOW_REMOTE"]);
/** Never handed to the child: they change how a runtime starts, not what ASCEND does. */
const DROP = new Set(["NODE_OPTIONS", "ELECTRON_RUN_AS_NODE"]);

/**
 * The sidecar's environment: the parent's, minus ASCEND_* (except PASS_THROUGH),
 * NODE_OPTIONS and ELECTRON_RUN_AS_NODE, and in the packaged app minus PYTHON* too
 * (the frozen sidecar needs none, and PYTHONPATH and friends could load other code).
 * Names are compared upper-cased because Windows environment names are case-insensitive.
 */
export function sidecarEnv(
  parent: NodeJS.ProcessEnv,
  opts: { isPackaged: boolean; port: number; dataDir: string },
): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = {};
  for (const [name, value] of Object.entries(parent)) {
    const key = name.toUpperCase();
    if (key.startsWith("ASCEND_") && !PASS_THROUGH.has(key)) continue;
    if (DROP.has(key)) continue;
    if (opts.isPackaged && key.startsWith("PYTHON")) continue;
    env[name] = value;
  }
  env.ASCEND_PORT = String(opts.port);
  env.ASCEND_DATA_DIR = opts.dataDir;
  return env;
}

export function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.unref();
    srv.on("error", reject);
    srv.listen(0, "127.0.0.1", () => {
      const address = srv.address();
      srv.close(() => (typeof address === "object" && address ? resolve(address.port) : reject(new Error("no port"))));
    });
  });
}

export class SidecarManager {
  readonly token = randomBytes(32).toString("hex");
  private child: ChildProcess | null = null;
  private stopping = false;
  private status: SidecarStatus = { state: "stopped", port: null, restarts: 0, lastError: null };
  private crashes: number[] = [];

  constructor(private readonly opts: SidecarOptions) {}

  get baseUrl(): string {
    return `http://127.0.0.1:${this.status.port}`;
  }

  getStatus(): SidecarStatus {
    return { ...this.status };
  }

  async start(): Promise<void> {
    this.stopping = false;
    const port = await freePort();
    this.status = { ...this.status, state: this.status.restarts ? "restarting" : "starting", port };
    const { command, args, cwd } = this.command();
    this.opts.log(`spawning sidecar: ${command} ${args.join(" ")} (port ${port})`);

    const child = spawn(command, args, {
      cwd,
      env: sidecarEnv(process.env, { isPackaged: this.opts.isPackaged, port, dataDir: this.opts.dataDir }),
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
    });
    this.child = child;
    child.stdin?.write(this.token + "\n");
    child.stdin?.end();
    child.stdout?.on("data", (b: Buffer) => this.opts.log(`[sidecar] ${b.toString().trimEnd()}`));
    child.stderr?.on("data", (b: Buffer) => this.opts.log(`[sidecar] ${b.toString().trimEnd()}`));
    child.on("exit", (code) => this.onExit(code));

    await this.waitHealthy();
    this.status = { ...this.status, state: "ready", lastError: null };
  }

  private command(): { command: string; args: string[]; cwd: string } {
    if (this.opts.isPackaged) {
      const exe = process.platform === "win32" ? "ascend-sidecar.exe" : "ascend-sidecar";
      const dir = path.join(this.opts.resourcesPath, "sidecar");
      return { command: path.join(dir, exe), args: [], cwd: dir };
    }
    const cwd = path.join(this.opts.devRoot, "services", "sidecar");
    if (!fs.existsSync(cwd)) throw new Error(`sidecar source not found at ${cwd}`);
    return { command: "uv", args: ["run", "python", "-m", "app"], cwd };
  }

  private async waitHealthy(): Promise<void> {
    const deadline = Date.now() + (this.opts.healthTimeoutMs ?? HEALTH_TIMEOUT_MS);
    const expected = healthProof(this.token);
    while (Date.now() < deadline) {
      let body: unknown = null;
      try {
        const res = await fetch(`${this.baseUrl}/health`, { signal: AbortSignal.timeout(HEALTH_POLL_TIMEOUT_MS) });
        if (res.ok) body = await res.json();
      } catch {
        /* not listening yet */
      }
      if (body !== null) {
        if ((body as { proof?: unknown }).proof === expected) return;
        // Something else answers on our port (it was taken after freePort()); never send
        // it the token. Our sidecar cannot bind and exits, which triggers a restart on a
        // new port.
        throw new Error(`port ${this.status.port} is answered by another process`);
      }
      await new Promise((r) => setTimeout(r, 300));
    }
    throw new Error("sidecar did not become healthy within 30 s");
  }

  private onExit(code: number | null): void {
    this.child = null;
    if (this.stopping) {
      this.status = { ...this.status, state: "stopped" };
      return;
    }
    this.opts.log(`sidecar exited unexpectedly (code ${code})`);
    // Count crashes in a sliding window: the old counter never reset, so three crashes
    // spread over days left the fourth one fatal (review L9).
    this.crashes = [...recentCrashes(this.crashes, Date.now()), Date.now()];
    if (this.crashes.length > MAX_RESTARTS) {
      this.status = { ...this.status, state: "failed", lastError: `exited with code ${code}` };
      return;
    }
    this.status = { ...this.status, restarts: this.crashes.length, state: "restarting" };
    const backoff = 500 * 2 ** this.status.restarts;
    setTimeout(() => {
      this.start().catch((err: Error) => {
        this.status = { ...this.status, state: "failed", lastError: err.message };
      });
    }, backoff);
  }

  async request(method: string, urlPath: string, body?: unknown): Promise<{ status: number; data: unknown }> {
    if (this.status.state !== "ready") throw new Error(`sidecar is ${this.status.state}`);
    // /events is a never-ending stream; through IPC it would hold the call forever.
    if (urlPath === "/events" || urlPath.startsWith("/events?")) throw new Error("/events is not available over IPC");
    const timeoutMs = this.opts.requestTimeoutMs ?? REQUEST_TIMEOUT_MS;
    // A hung sidecar used to leave the renderer's call (and its spinner) waiting forever
    // (review L10).
    const res = await fetch(`${this.baseUrl}${urlPath}`, {
      method,
      signal: AbortSignal.timeout(timeoutMs),
      headers: {
        Authorization: `Bearer ${this.token}`,
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const type = res.headers.get("content-type") ?? "";
    const data = res.status === 204 ? null : type.includes("json") ? await res.json() : await res.text();
    return { status: res.status, data };
  }

  /** Ask the sidecar to exit cleanly; kill it if it hasn't after 3 s. */
  async stop(): Promise<void> {
    this.stopping = true;
    const child = this.child;
    if (!child) return;
    try {
      await this.request("POST", "/shutdown");
    } catch {
      /* already gone */
    }
    await new Promise<void>((resolve) => {
      const timer = setTimeout(() => {
        child.kill();
        resolve();
      }, 3000);
      child.once("exit", () => {
        clearTimeout(timer);
        resolve();
      });
    });
  }
}
