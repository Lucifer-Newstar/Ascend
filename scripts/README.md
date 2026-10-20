# scripts/

Windows helpers (PowerShell). Each one is a short list of the same commands the README shows.

| Script | What it does |
|---|---|
| `setup.ps1` | Checks git/node, installs `uv` if missing, installs Python 3.12 next to your existing Python, syncs sidecar deps, applies migrations, runs `npm install`, checks for Ollama. |
| `dev-browser.ps1` | Opens two terminals: the sidecar in dev mode and the Vite dev server, so you can work on the UI in a browser. |

If PowerShell blocks scripts, run them with `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1`.
