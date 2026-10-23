/**
 * The packaging config points at files under apps/desktop/build/. They were once caught by
 * an unanchored `build/` in .gitignore, so they existed only on one machine and the
 * installer job failed on a clean checkout. CI runs on a clean checkout, so "exists" here
 * means "is committed"; the git check covers a local working copy too.
 */
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

import { describe, expect, it } from "vitest";

const desktop = path.resolve(__dirname, "..");
const config = fs.readFileSync(path.join(desktop, "electron-builder.yml"), "utf8");

function referenced(): string[] {
  const keys = ["afterPack", "icon", "installerIcon", "uninstallerIcon"];
  const out = new Set<string>();
  for (const key of keys) {
    for (const m of config.matchAll(new RegExp(`^\\s*${key}:\\s*(\\S+)\\s*$`, "gm"))) out.add(m[1]);
  }
  return [...out];
}

function ignored(file: string): boolean {
  try {
    execFileSync("git", ["check-ignore", "-q", file], { cwd: desktop, stdio: "ignore" });
    return true; // exit 0: the path is ignored
  } catch {
    return false;
  }
}

describe("electron-builder resources", () => {
  it("references the fuses hook and the icon", () => {
    expect(referenced()).toEqual(expect.arrayContaining(["build/fuses.cjs", "build/icon.ico"]));
  });

  it.each(referenced())("%s exists and is not git-ignored", (file) => {
    expect(fs.existsSync(path.join(desktop, file))).toBe(true);
    expect(ignored(file)).toBe(false);
  });
});

describe("Electron fuses hook", () => {
  it("decides every fuse @electron/fuses knows (Electron 45 has nine)", async () => {
    const { FuseV1Options } = await import("@electron/fuses");
    const known = Object.keys(FuseV1Options).filter((key) => Number.isNaN(Number(key)));
    const { FUSES } = createRequire(__filename)(path.join(desktop, "build/fuses.cjs")) as {
      FUSES: Record<string, boolean>;
    };
    expect(known).toContain("WasmTrapHandlers");
    expect(Object.keys(FUSES).sort()).toEqual([...known].sort());
  });
});
