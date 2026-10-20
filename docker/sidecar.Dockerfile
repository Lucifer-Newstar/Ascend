# syntax=docker/dockerfile:1
# Sidecar image for DEVELOPMENT and CI TESTS only. End users never run Docker:
# the desktop app ships the PyInstaller build instead.
#
# Build context is services/sidecar (see docker-compose.yml).
#   docker build -f docker/sidecar.Dockerfile --target test services/sidecar

ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.5.11

# uv is copied from its own image; a named stage lets the version be a build arg.
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# ---- base: Python + uv ------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS base
COPY --from=uv /uv /uvx /bin/
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
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
ARG VERSION=dev
LABEL org.opencontainers.image.title="ascend-sidecar" \
      org.opencontainers.image.description="ASCEND local engine (development image)" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/Lucifer-Newstar/Ascend-"
# Code is owned by root and read-only to the app user; only /data is writable,
# so the container also runs with a read-only root filesystem (see compose).
COPY --chown=root:root app ./app
COPY --chown=root:root alembic ./alembic
COPY --chown=root:root alembic.ini ./
# Fixed, non-root UID/GID so volume permissions are predictable on any host.
RUN groupadd --system --gid 10001 ascend \
    && useradd --system --uid 10001 --gid ascend --no-create-home --shell /usr/sbin/nologin ascend \
    && mkdir -p /data && chown ascend:ascend /data
USER 10001:10001
ENV PATH=/app/.venv/bin:$PATH \
    ASCEND_DATA_DIR=/data \
    ASCEND_HOST=0.0.0.0 \
    ASCEND_PORT=8765
VOLUME ["/data"]
EXPOSE 8765
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=2)"]
# --dev: token "dev" unless ASCEND_TOKEN is set, and CORS for the Vite dev server.
CMD ["python", "-m", "app", "--dev"]
