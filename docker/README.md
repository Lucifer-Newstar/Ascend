# docker/

Containers for **development and CI only**. ASCEND itself is a desktop app and never needs
Docker on a user's PC; the installer ships a PyInstaller build of the sidecar.

| File | What it is |
|---|---|
| `sidecar.Dockerfile` | Multi-stage image: `deps` (locked runtime deps via uv), `test` (adds ruff/pytest, runs them), `runtime` (serves the API on port 8765 as a non-root user). |
| `docker-compose.yml` | `sidecar-tests` runs lint + tests in a clean container; `sidecar` runs the API with a named volume for its SQLite file. |

```bash
# from the repo root
docker compose -f docker/docker-compose.yml run --rm sidecar-tests
docker compose -f docker/docker-compose.yml up --build sidecar
# then open http://localhost:8765/docs  (dev token: "dev")
```

Notes

- The build context is `services/sidecar`, so `services/sidecar/.dockerignore` keeps `.venv`
  and local databases out of the image.
- `uv sync --frozen` fails the build if `uv.lock` is out of date with `pyproject.toml`; run
  `uv lock` and commit the lockfile.
- The `runtime` stage binds `0.0.0.0` *inside* the container (ASCEND_HOST); compose publishes
  it on `127.0.0.1` only. On a desktop the sidecar always binds `127.0.0.1`.
- On Windows, Docker Desktop with the WSL2 backend works as-is.
