import { describe, expect, it } from "vitest";

import { sidecarEnv } from "./sidecar";

const parent = {
  PATH: "/usr/bin",
  APPDATA: "C:\\Users\\me\\AppData\\Roaming",
  ASCEND_TOKEN: "dev",
  ASCEND_HOST: "0.0.0.0",
  Ascend_Db_Url: "sqlite:///elsewhere.db",
  ASCEND_DEV: "1",
  ASCEND_PORT: "1",
  ASCEND_COACH_MODEL: "llama3.2:3b",
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
