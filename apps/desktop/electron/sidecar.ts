/**
 * Sidecar lifecycle: spawn the Python API, wait until healthy, restart on crash.
 *
 *  1. pick a free localhost port (bind :0, read the port, close)
 *  2. generate a random 256-bit token for this launch
 *  3. spawn the sidecar: dev = `uv run python -m app` in services/sidecar,
 *     packaged = resources/sidecar/ascend-sidecar(.exe) built by PyInstaller
 *  4. write the token on its stdin (never in argv/env, so it isn't visible in
 *     the process list)
 *  5. poll GET /health until 200 (timeout 30 s)
 *  6. on unexpected exit: restart with backoff, up to MAX_RESTARTS
 */
import { ChildProcess, spawn } from "node:child_process";
import { randomBytes } from "node:crypto";
import fs from "node:fs";
import net from "node:net";
import path from "node:path";

import type { SidecarStatus } from "@ascend/shared";

const HEALTH_TIMEOUT_MS = 30_000;
const MAX_RESTARTS = 3;

export interface SidecarOptions {
  isPackaged: boolean;
  resourcesPath: string;
  /** Repo root in development (apps/desktop/../..). */
  devRoot: string;
  dataDir: string;
  log: (line: string) => void;
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
      env: { ...process.env, ASCEND_PORT: String(port), ASCEND_DATA_DIR: this.opts.dataDir },
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
    const deadline = Date.now() + HEALTH_TIMEOUT_MS;
    while (Date.now() < deadline) {
      try {
        const res = await fetch(`${this.baseUrl}/health`);
        if (res.ok) return;
      } catch {
        /* not listening yet */
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
    if (this.status.restarts >= MAX_RESTARTS) {
      this.status = { ...this.status, state: "failed", lastError: `exited with code ${code}` };
      return;
    }
    this.status = { ...this.status, restarts: this.status.restarts + 1, state: "restarting" };
    const backoff = 500 * 2 ** this.status.restarts;
    setTimeout(() => {
      this.start().catch((err: Error) => {
        this.status = { ...this.status, state: "failed", lastError: err.message };
      });
    }, backoff);
  }

  async request(method: string, urlPath: string, body?: unknown): Promise<{ status: number; data: unknown }> {
    if (this.status.state !== "ready") throw new Error(`sidecar is ${this.status.state}`);
    const res = await fetch(`${this.baseUrl}${urlPath}`, {
      method,
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
