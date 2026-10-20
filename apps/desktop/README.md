# apps/desktop: Electron shell + React renderer

```
electron/
  main.ts       window, security settings, IPC handlers, app lifecycle
  sidecar.ts    starts the Python sidecar: free port, token on stdin, /health, restart
  preload.ts    exposes window.ascend (typed AscendBridge) via contextBridge
  channels.ts   IPC channel names, checked against @ascend/shared at compile time
src/
  api/client.ts      typed calls; IPC in Electron, fetch() in browser dev mode
  components/        Layout, Rings, XpBar, QuestList, MuscleMap, Toast, States, Icons
  pages/             Onboarding, Dashboard, Workout, Diet, Coach, History, Settings
  lib/               pure helpers (+ *.test.ts for vitest)
electron-builder.yml Windows NSIS installer config
```

## Run

```bash
npm install                         # from the repo root (npm workspaces)
npm run dev:electron -w apps/desktop   # full app; Electron spawns the sidecar via `uv run`
```

UI work in a normal browser (fast reload, no Electron):

```bash
cd services/sidecar && uv run python -m app --dev     # terminal 1
npm run dev -w apps/desktop                            # terminal 2 -> http://localhost:5173
```

## Security model

- `contextIsolation: true`, `sandbox: true`, `nodeIntegration: false`.
- The renderer only sees `window.ascend` (4 functions). It never sees the sidecar token.
- Main validates every IPC request (method allow-list, path must start with `/`).
- Navigation is blocked; external `https://` links open in the default browser.
- A strict Content-Security-Policy in `index.html`: no remote scripts, fonts are bundled.

## Scripts

| Script | |
|---|---|
| `dev` | Vite dev server (browser) |
| `dev:electron` | Vite + Electron together |
| `build` | type-check, `vite build` → `dist/`, compile Electron → `dist-electron/` |
| `typecheck` / `lint` / `test` | tsc / eslint / vitest |
| `dist:win` | build + electron-builder → `release/ASCEND-Setup-x.y.z.exe` (needs the sidecar build first) |

## Packaging

The Windows installer is electron-builder's NSIS target (`electron-builder.yml`):

- **Per-user install**, no admin prompt: `%LOCALAPPDATA%\Programs\ASCEND`. The user can
  pick another folder. Desktop and Start-menu shortcuts are created.
- **Data is kept** on uninstall (`%APPDATA%\ASCEND`), so a reinstall finds the same database.
- **The sidecar** is the PyInstaller one-folder build from `services/sidecar/dist/ascend-sidecar`,
  copied to `resources/sidecar/` as an extra resource.
- **Fuses** (`build/fuses.cjs`, run as `afterPack`): RunAsNode, `NODE_OPTIONS` and `--inspect`
  are switched off in the binary, ASAR integrity validation is on, and the app only loads
  from `app.asar`. Check a binary with `npx electron-fuses read --app <exe>`.
- **Icons** come from `build/icon.png` / `build/icon.ico`, rendered by `scripts/make_icons.py`.

Build it on Windows:

```bash
make build-sidecar                              # services/sidecar/dist/ascend-sidecar/
cd services/sidecar && uv run python packaging/smoke.py   # start, /health, /shutdown
make dist-win                                   # apps/desktop/release/ASCEND-Setup-x.y.z.exe
```

CI builds the same installer on every push to `main` that touches the app and on `v*`
tags (`.github/workflows/release.yml`); download it from the run's artefacts. The build
is unsigned for now, so SmartScreen shows "unknown publisher" on first run.

## Theme

Dark, restrained cyan accent (`#22D3EE`), violet XP (`#8B7CFF`), status colours shared with the
muscle map: under `#4F7BD9`, optimal `#22C55E`, recovering `#F5A524`, over `#EF4444`.
Tokens live in `src/index.css` (`@theme`). Fonts: Inter and Rajdhani, bundled via `@fontsource`.
