# scripts/

Windows helpers (PowerShell), each a short list of the same commands the README shows, and
the Python tools CI and the maintainers run.

| Script | What it does |
|---|---|
| `setup.ps1` | Checks git/node, installs `uv` if missing, installs Python 3.12 next to your existing Python, syncs sidecar deps, applies migrations, runs `npm install`, checks for Ollama. |
| `dev-browser.ps1` | Opens two terminals: the sidecar in dev mode and the Vite dev server, so you can work on the UI in a browser. |
| `check_contract_drift.py` | Compares the sidecar's OpenAPI with `docs/contracts` (`make contracts`; CI job "sidecar"). |
| `sync_contract.py` | Copies operations or schemas from the sidecar's OpenAPI into a `docs/contracts` file after an API change. |
| `check_md_links.py` | Fails when a relative link in a Markdown file points at a missing file or heading (CI job "docs"). |
| `make_icons.py` | Renders `apps/desktop/build/icon.png` and `icon.ico`. |
| `build_exercise_library.py` | Rebuilds the bundled exercise library (and with `--images` the 320 px photos) from free-exercise-db; needs network once. |
| `body_map/` | Generator and notes for the muscle map artwork (`build_map.py`). |

If PowerShell blocks scripts, run them with `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1`.
