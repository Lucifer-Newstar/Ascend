/**
 * electron-builder afterPack hook: flip Electron fuses on the packed binary.
 *
 * Fuses are bits baked into the Electron executable that switch features off
 * for good, before the app is signed. ASCEND only ever runs its own bundled
 * code, so everything that lets someone repurpose the binary is turned off:
 *
 *   RunAsNode                        off  ELECTRON_RUN_AS_NODE can't turn ASCEND.exe into node.exe
 *   EnableNodeOptionsEnvironmentVariable off  NODE_OPTIONS can't inject --require
 *   EnableNodeCliInspectArguments    off  --inspect can't attach a debugger
 *   EnableCookieEncryption           on   cookies on disk are OS-encrypted
 *   EnableEmbeddedAsarIntegrityValidation on  app.asar is checked against its header hash
 *   OnlyLoadAppFromAsar              on   a loose resources/app folder is ignored
 *
 * Run standalone:
 *   node build/fuses.cjs <path-to-electron-exe>           flip the fuses on a binary
 *   node build/fuses.cjs --check <path-to-electron-exe>   exit 1 unless every fuse above
 *                                                         is set as listed (used in CI)
 *
 * Left at Electron's default: LoadBrowserProcessSpecificV8Snapshot (no custom snapshot)
 * and GrantFileProtocolExtraPrivileges (the window loads dist/index.html over file://).
 */
const path = require("node:path");
const { flipFuses, getCurrentFuseWire, FuseState, FuseV1Options, FuseVersion } = require("@electron/fuses");

const FUSES = {
  version: FuseVersion.V1,
  [FuseV1Options.RunAsNode]: false,
  [FuseV1Options.EnableNodeOptionsEnvironmentVariable]: false,
  [FuseV1Options.EnableNodeCliInspectArguments]: false,
  [FuseV1Options.EnableCookieEncryption]: true,
  [FuseV1Options.EnableEmbeddedAsarIntegrityValidation]: true,
  [FuseV1Options.OnlyLoadAppFromAsar]: true,
};

function executablePath(context) {
  const { appOutDir, packager, electronPlatformName } = context;
  const name = packager.appInfo.productFilename;
  if (electronPlatformName === "win32") return path.join(appOutDir, `${name}.exe`);
  if (electronPlatformName === "darwin") return path.join(appOutDir, `${name}.app`);
  return path.join(appOutDir, packager.executableName ?? name);
}

async function applyFuses(binary) {
  // resetAdHocDarwinSignature only matters on macOS arm64; harmless elsewhere.
  await flipFuses(binary, { ...FUSES, resetAdHocDarwinSignature: binary.endsWith(".app") });
}

/** Compare a binary's fuse wire with FUSES; returns the names of fuses set differently. */
async function checkFuses(binary) {
  const wire = await getCurrentFuseWire(binary);
  const wrong = [];
  for (const [key, want] of Object.entries(FUSES)) {
    if (key === "version") continue;
    const expected = want ? FuseState.ENABLE : FuseState.DISABLE;
    const name = FuseV1Options[Number(key)];
    const ok = wire[key] === expected;
    console.log(`${ok ? "ok   " : "WRONG"} ${name} = ${want ? "Enabled" : "Disabled"}`);
    if (!ok) wrong.push(name);
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
  if (check) {
    checkFuses(path.resolve(target)).then(
      (wrong) => process.exit(wrong.length ? 1 : 0),
      (err) => {
        console.error(err);
        process.exit(1);
      },
    );
    return;
  }
  applyFuses(path.resolve(target)).then(
    () => console.log(`fuses flipped on ${target}`),
    (err) => {
      console.error(err);
      process.exit(1);
    },
  );
}
