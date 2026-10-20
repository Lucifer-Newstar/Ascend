# syntax=docker/dockerfile:1
# Sidecar image for DEVELOPMENT and CI TESTS only. End users never run Docker:
# the desktop app ships the PyInstaller build instead.
#
# Build context is services/sidecar (see docker-compose.yml).
#   docker build -f docker/sidecar.Dockerfile --target test services/sidecar

ARG PYTHON_VERSION=3.12

# ---- base: Python + uv ------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app

# ---- deps: install locked runtime dependencies (cached layer) -----------------
FROM base AS deps
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# ---- test: + dev tools and tests; default command runs lint + tests ------------
FROM deps AS test
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --group dev
COPY . .
CMD ["sh", "-c", "uv run ruff check . && uv run pytest -q"]

# ---- runtime: the API itself, for poking at it from a browser -----------------
FROM deps AS runtime
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
# Non-root user; data lives in a volume.
RUN useradd --create-home ascend && mkdir -p /data && chown ascend /data
USER ascend
ENV ASCEND_DATA_DIR=/data \
    ASCEND_HOST=0.0.0.0 \
    ASCEND_PORT=8765
EXPOSE 8765
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health')"
CMD ["/app/.venv/bin/python", "-m", "app", "--dev"]
