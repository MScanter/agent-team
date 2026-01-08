# agent-team - Backend

This backend runs in **single-user mode** (no login).

User settings and executions are persisted locally via **SQLite**:
- `agents` / `teams` / `model_configs` survive restarts
- `executions` and `messages` also survive restarts

## Requirements

- Python 3.13+

## Setup (pip)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

## Setup (uv)

```bash
cd backend
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
python -m app.main
```

## Notes

- LLM credentials are configured in the frontend (“API配置”) and sent to the backend per execution (no backend env/secret config).

## Persistence

By default the backend stores SQLite at the OS app-data location:
- macOS: `~/Library/Application Support/agent-team/app.db`
- Linux: `${XDG_DATA_HOME:-~/.local/share}/agent-team/app.db`
- Windows: `%LOCALAPPDATA%\\agent-team\\app.db`

Override the DB location (useful for development) with:
- `STORE_SQLITE_PATH=backend/data/app.dev.db`

You can also force in-memory mode with:
- `STORE_BACKEND=memory`

### Using `.env` (recommended)

This repo includes `backend/.env.example`. Copy it to `backend/.env` and edit as needed:
- `cp backend/.env.example backend/.env`

The backend automatically loads, in order:
- `backend/.env`
- `backend/.env.local`
- `backend/.env.example` (fallback)
