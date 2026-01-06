# Agent Team Builder - Backend

This backend runs in **single-user mode** and uses an **in-memory store** (no database, no login). Data resets when the server restarts.

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
