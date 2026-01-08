# agent-team

Single-machine (no auth) app to build agent teams and run discussions.

## Quickstart

### Backend

```bash
cd backend

# Optional but recommended: use repo-local DB in development
cp .env.example .env

# Create venv + install deps (pick one)
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
# or: uv venv && source .venv/bin/activate && uv pip install -r requirements.txt

python -m app.main
```

Backend persists `agents / teams / model_configs / executions / messages` via SQLite (see `backend/README.md`).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Development Notes

- `STORE_SQLITE_PATH` can be set in `backend/.env` (auto-loaded) to control where SQLite lives.
- `STORE_BACKEND=memory` disables persistence (useful for quick demos).
- Execution streaming uses WebSocket at `/api/executions/{id}/ws`.
