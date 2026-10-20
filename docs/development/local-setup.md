# Local Setup — Windows 11

> One-time machine setup for every ASCEND developer, then the daily commands. Written for
> **Windows 11 + PowerShell**; commands for folders that do not exist yet in the repo are
> marked with the phase that adds them. Owner: Gokul (keep it working), all (report gaps).

---

## 1. Hardware and OS

| | Minimum | Reference laptop (Navin) |
|---|---|---|
| OS | Windows 11 22H2+ (64-bit) | Windows 11 |
| CPU | 4 cores | AMD Ryzen 7 7435HS (8 cores) |
| RAM | 8 GB (AI in rules/lite mode) | 12 GB |
| GPU | none (rules mode) · NVIDIA ≥ 4 GB VRAM for local AI | RTX 3050 Laptop, 4 GB |
| Disk free | 15 GB (repo, deps, models) | 200+ GB |
| Virtualisation | Enabled in BIOS (for WSL2/Docker) | WSL2 + Docker Desktop installed |

No NVIDIA GPU? You can still build everything; set AI to **off** or **lite** in the app and
skip the AI tests (`pytest -m "not gpu"`).

## 2. Install the tools

Open **PowerShell** (not as admin unless noted).

```powershell
# Git, GitHub CLI, VS Code
winget install --id Git.Git -e
winget install --id GitHub.cli -e
winget install --id Microsoft.VisualStudioCode -e

# Node.js — any version >= 20 works (root package.json "engines"); CI uses the current LTS.
# If you already have Node (e.g. 26), keep it:
node --version

# uv (Python manager) — then Python 3.12 *beside* any existing Python (3.14 is fine to keep)
winget install --id astral-sh.uv -e
uv python install 3.12
uv python list            # 3.12 and your system Python both listed

# Docker Desktop (WSL2 backend) — needed for MLflow, training image, Grafana (Phase 1+)
wsl --install             # only if `wsl --status` says WSL is not installed (admin, reboot)
winget install --id Docker.DockerDesktop -e

# Ollama — local AI runtime (skip if you have no GPU and will use rules mode)
winget install --id Ollama.Ollama -e
```

Restart the terminal after installing so `PATH` updates.

### Check everything

```powershell
git --version; gh --version; node --version; npm --version
uv --version; uv run --python 3.12 python --version
docker --version; wsl --status
ollama --version
nvidia-smi --query-gpu=name,memory.total --format=csv   # NVIDIA only
```

## 3. Git and GitHub

```powershell
git config --global user.name  "<your name or GitHub username>"
git config --global user.email "<the email on your GitHub account>"
git config --global core.autocrlf input      # repo uses LF (.editorconfig / .gitattributes)
git config --global core.longpaths true      # node_modules paths on Windows
git config --global init.defaultBranch main
gh auth login                                # HTTPS + browser login is easiest
```

Turn on 2FA on GitHub before the kickoff. Commits are dated when you make them —
never change dates (working-rules rule 4).

## 4. Clone and install

```powershell
gh repo clone <org-or-user>/ascend
cd ascend

# TypeScript workspaces (apps/desktop, packages/shared)
npm install

# Python sidecar (creates services/sidecar/.venv with Python 3.12)
cd services/sidecar
uv sync
uv run alembic upgrade head      # creates/migrates the dev database
uv run pytest                    # unit + API tests
cd ../..
```

## 5. Run it

Two ways, both from the repo root:

**A. Full desktop app (Electron spawns the sidecar itself):**

```powershell
npm run dev:electron -w apps/desktop
```

Main finds a free port, starts `uv run python -m app` in `services/sidecar`, passes the
token on stdin and waits for `/health`.

**B. Browser UI + standalone sidecar (fast UI iteration):**

```powershell
# terminal 1
cd services/sidecar; uv run python -m app --dev    # 127.0.0.1:8765, token "dev", CORS for Vite
# terminal 2
npm run dev                                        # Vite on http://localhost:5173
```

API docs while the dev sidecar runs: <http://127.0.0.1:8765/docs> (schema only, no data).

**C. UI against the contract mock (no backend needed):**

```powershell
npx @stoplight/prism-cli mock docs/contracts/workouts.yaml -p 4010
```

See [contracts/README.md §3](../contracts/README.md#3-mock-server-frontend-development).

## 6. Local AI (optional, GPU)

```powershell
ollama pull qwen3:4b        # coach, ~2.5 GB
ollama pull qwen3-vl:2b     # meal item finder, ~1.9 GB (Phase 2)
ollama pull qwen3:1.7b      # lite tier, ~1.4 GB
ollama run qwen3:4b "Say hi in Tamil and English" --verbose   # shows eval rate (tokens/s)
ollama ps                   # what is loaded and on GPU/CPU
```

Only one of the two big models fits in 4 GB VRAM at a time; that is expected
([system-architecture.md §10](../architecture/system-architecture.md#10-model-manager)).
The sidecar reads `OLLAMA_HOST` (default `http://127.0.0.1:11434`) and
`ASCEND_COACH_MODEL` (default `qwen3:4b`).

## 7. Docker + WSL2 for ML and dev observability (Phase 1+)

```powershell
# Docker Desktop → Settings → General: "Use the WSL 2 based engine" ✔
docker run --rm hello-world
# GPU inside containers (NVIDIA driver on Windows is enough; no driver inside WSL)
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi

# MLflow tracking server (file arrives in Phase 1)
docker compose -f infra/compose/mlflow.yml up -d       # http://127.0.0.1:5000
# Prometheus + Grafana for the dev sidecar (Phase 2)
docker compose -f infra/compose/observability.yml up -d # :9090, :3000
```

Give Docker enough memory on a 12 GB machine: create `%UserProfile%\.wslconfig` with

```ini
[wsl2]
memory=6GB
swap=4GB
```

then `wsl --shutdown` and restart Docker Desktop. Stop the ML stack when not training —
Ollama, Docker and Electron together are tight on 12 GB.

## 8. Quality tools (Phase 0)

```powershell
uvx pre-commit install           # runs ruff, mypy, eslint, prettier, gitleaks on commit
cd services/sidecar
uv run ruff check . ; uv run ruff format --check . ; uv run mypy app
cd ../..
npm run lint; npm run typecheck; npm test
```

## 9. Build an installer locally (Gokul's lane, anyone can run it)

```powershell
cd services/sidecar
uv sync --group build
uv run --group build pyinstaller packaging/ascend-sidecar.spec --noconfirm   # → dist/ascend-sidecar/
cd ../..
npm run dist:win -w apps/desktop                 # electron-builder NSIS, no publish
```

The installer lands in the output folder set in the electron-builder config (Gokul
records the final path here once the Phase 0 config is merged).

## 10. Where things live on your PC

| What | Path |
|---|---|
| App data (DB, photos, logs) | `%APPDATA%\ASCEND` (`ASCEND_DATA_DIR` overrides; tests use a temp dir) |
| Ollama models | Ollama's own store (`%UserProfile%\.ollama\models`) |
| DVC cache | `ml/.dvc/cache` + the remote you configure (external drive) |

Ports and environment variables: [port-register.md](../architecture/port-register.md).

## 11. Troubleshooting

| Symptom | Fix |
|---|---|
| `uv run` uses Python 3.14 | Run inside `services/sidecar` (it has `.python-version` = 3.12) or `uv python pin 3.12` |
| PowerShell blocks scripts | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Sidecar never becomes healthy | Run `uv run python -m app --dev` alone and read the error; check `alembic upgrade head` |
| Port 8765 / 5173 / 5000 / 3000 in use | `Get-NetTCPConnection -LocalPort 8765`; stop the process or change the dev port |
| Antivirus deletes the built `ascend-sidecar.exe` | Expected sometimes with PyInstaller; add a dev-folder exclusion, report it (edge case E2) |
| `ollama` uses CPU only | `ollama ps` shows 100% CPU → another GPU app holds VRAM, or the model is too large; try `qwen3:1.7b` |
| Docker can't see the GPU | Update the NVIDIA Windows driver; Docker Desktop ≥ WSL2 backend; `wsl --update` |
| Long path errors in `node_modules` | `git config --global core.longpaths true`; enable Win32 long paths in Group Policy |
