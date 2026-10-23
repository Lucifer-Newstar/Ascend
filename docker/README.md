# docker/

Containers for **development and CI only**. ASCEND itself is a desktop app and never needs
Docker on a user's PC; the installer ships a PyInstaller build of the sidecar.

| File | What it is |
|---|---|
| `sidecar.Dockerfile` | Multi-stage image: `deps` (locked runtime deps via uv), `test` (adds ruff/pytest, runs them), `runtime` (serves the API on port 8765 as UID 10001). |
| `docker-compose.yml` | Four profiles, so nothing starts unless you ask for it (below). |

## Profiles

| Profile | Services | Make target | Open |
|---|---|---|---|
| `test` | `sidecar-tests`: ruff + pytest in a clean container | `make docker-test` | n/a |
| `dev` | `sidecar`: the API with a named volume for its SQLite file | `make docker-dev` | http://localhost:8765/docs (token `dev`) |
| `web` | `sidecar` + `web` (Vite dev server for the renderer, source mounted) | `make docker-web` | http://localhost:5173 |
| `ml` | `mlflow`: tracking server, runs and artefacts in the `mlflow-data` volume | `make docker-mlflow` | http://localhost:5000 |

`make docker-down` stops everything and keeps the volumes. To point Navin's pipeline at the
container: `MLFLOW_TRACKING_URI=http://localhost:5000 dvc repro` in `ml/`.

## Hardening

Long-running services share one `x-hardened` block in the compose file:

- **read-only root filesystem**; only the data volume and a `/tmp` tmpfs are writable;
- **all Linux capabilities dropped** and `no-new-privileges` set;
- the runtime image runs as a **fixed non-root UID/GID (10001)** and the code is owned by root,
  so the process cannot modify it even if it is compromised;
- ports are published on **127.0.0.1 only**; the `runtime` stage binds `0.0.0.0` *inside* the
  container (ASCEND_HOST). On a desktop the sidecar always binds `127.0.0.1`.
- a `HEALTHCHECK` polls `/health`; `web` waits for the sidecar to be healthy.

CI (`.github/workflows/ci.yml`, job `docker`) lints the Dockerfile with hadolint, validates
every profile with `docker compose config`, runs the tests in the `test` image and starts the
runtime image with the same flags until it reports healthy.

## Notes

- The build context is `services/sidecar`, so `services/sidecar/.dockerignore` keeps `.venv`,
  build output, coverage and local databases out of the image.
- `uv sync --frozen` fails the build if `uv.lock` is out of date with `pyproject.toml`; run
  `uv lock` and commit the lockfile.
- `ARG UV_VERSION` and `ARG PYTHON_VERSION` pick the toolchain; bump base images by hand.
- On Windows, Docker Desktop with the WSL2 backend works as-is. On Linux engines compose maps
  `host.docker.internal` to the host so the sidecar can still reach a host Ollama.
