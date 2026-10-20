# ASCEND sidecar

The local FastAPI process that holds all of ASCEND's logic and the SQLite database.
Electron starts it on a random localhost port and talks to it with a per-launch token.

```bash
uv sync                      # create .venv with Python 3.12 + deps
uv run alembic upgrade head  # create / migrate the database
uv run pytest                # run tests
uv run python -m app --dev   # run standalone on 127.0.0.1:8765 with token "dev"
```
