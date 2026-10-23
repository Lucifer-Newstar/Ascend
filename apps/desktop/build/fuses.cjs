/**
 * electron-builder afterPack hook: flip Electron fuses on the packed binary.
 *
 * Fuses are bits baked into the Electron executable that switch features off
 * for good, before the app is signed. ASCEND only ever runs its own bundled
 * code, so everything that lets someone repurpose the binary is turned off.
 * Every fuse Electron 45 has is set explicitly (strictlyRequireAllFuses), so an
 * Electron upgrade that adds a fuse fails the build until it is decided here:
 *
 *   RunAsNode                             off  ELECTRON_RUN_AS_NODE can't turn ASCEND.exe into node.exe
 *   EnableCookieEncryption                on   cookies on disk are OS-encrypted
 *   EnableNodeOptionsEnvironmentVariable  off  NODE_OPTIONS can't inject --require
 *   EnableNodeCliInspectArguments         off  --inspect can't attach a debugger
 *   EnableEmbeddedAsarIntegrityValidation on   app.asar is checked against its header hash
 *   OnlyLoadAppFromAsar                   on   a loose resources/app folder is ignored
 *   LoadBrowserProcessSpecificV8Snapshot  off  (Electron default) no custom snapshot
 *   GrantFileProtocolExtraPrivileges      on   (Electron default) the window loads dist/index.html over file://
 *   WasmTrapHandlers                      on   (Electron default) V8's WebAssembly trap handlers
 *
 * @electron/fuses 2.x is ESM-only, so it is loaded with import() from this CommonJS hook.
 *
 * Run standalone:
 *   node build/fuses.cjs <path-to-electron-exe>           flip the fuses on a binary
 *   node build/fuses.cjs --check <path-to-electron-exe>   exit 1 unless every fuse above
 *                                                         is set as listed (used in CI)
 */
const path = require("node:path");

/** Wanted state of every fuse, by @electron/fuses' FuseV1Options name. */
const FUSES = {
  RunAsNode: false,
  EnableCookieEncryption: true,
  EnableNodeOptionsEnvironmentVariable: false,
  EnableNodeCliInspectArguments: false,
  EnableEmbeddedAsarIntegrityValidation: true,
  OnlyLoadAppFromAsar: true,
  LoadBrowserProcessSpecificV8Snapshot: false,
  GrantFileProtocolExtraPrivileges: true,
  WasmTrapHandlers: true,
};

const loadFuses = () => import("@electron/fuses");

/** FUSES as the config object flipFuses() takes. */
async function fuseConfig() {
  const { FuseV1Options, FuseVersion } = await loadFuses();
  const config = { version: FuseVersion.V1, strictlyRequireAllFuses: true };
  for (const [name, want] of Object.entries(FUSES)) {
    const index = FuseV1Options[name];
    if (index === undefined) throw new Error(`@electron/fuses does not know the fuse ${name}`);
    config[index] = want;
  }
  return config;
}

function executablePath(context) {
  const { appOutDir, packager, electronPlatformName } = context;
  const name = packager.appInfo.productFilename;
  if (electronPlatformName === "win32") return path.join(appOutDir, `${name}.exe`);
  if (electronPlatformName === "darwin") return path.join(appOutDir, `${name}.app`);
  return path.join(appOutDir, packager.executableName ?? name);
}

async function applyFuses(binary) {
  const { flipFuses } = await loadFuses();
  // resetAdHocDarwinSignature only matters on macOS arm64; harmless elsewhere.
  await flipFuses(binary, { ...(await fuseConfig()), resetAdHocDarwinSignature: binary.endsWith(".app") });
}

/**
 * Compare a binary's fuse wire with FUSES; returns the names of fuses set differently,
 * plus any fuse in the binary that FUSES does not decide.
 */
async function checkFuses(binary) {
  const { getCurrentFuseWire, FuseV1Options, FuseState } = await loadFuses();
  const wire = await getCurrentFuseWire(binary);
  const wrong = [];
  for (const [name, want] of Object.entries(FUSES)) {
    const expected = want ? FuseState.ENABLE : FuseState.DISABLE;
    const ok = wire[FuseV1Options[name]] === expected;
    console.log(`${ok ? "ok   " : "WRONG"} ${name} = ${want ? "Enabled" : "Disabled"}`);
    if (!ok) wrong.push(name);
  }
  const known = new Set(Object.keys(FUSES).map((name) => String(FuseV1Options[name])));
  for (const key of Object.keys(wire)) {
    if (key === "version" || known.has(key)) continue;
    const name = FuseV1Options[Number(key)] ?? `fuse #${key}`;
    console.log(`WRONG ${name} is in the binary but not decided in build/fuses.cjs`);
    wrong.push(name);
  }
  return wrong;
}

module.exports = async function afterPack(context) {
  await applyFuses(executablePath(context));
};
module.exports.FUSES = FUSES;
module.exports.applyFuses = applyFuses;
module.exports.checkFuses = checkFuses;

if (require.main === module) {
  const check = process.argv[2] === "--check";
  const target = process.argv[check ? 3 : 2];
  if (!target) {
    console.error("usage: node build/fuses.cjs [--check] <electron-binary>");
    process.exit(2);
  }
  const run = check
    ? checkFuses(path.resolve(target)).then((wrong) => process.exit(wrong.length ? 1 : 0))
    : applyFuses(path.resolve(target)).then(() => console.log(`fuses flipped on ${target}`));
  run.catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
