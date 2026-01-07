"""
In-memory application store (single-user, no database).
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4


def utcnow() -> datetime:
    return datetime.utcnow()


LOCAL_USER_ID = "local"


def _backend_root() -> Path:
    # backend/app/store.py -> backend/
    return Path(__file__).resolve().parents[1]


def _load_dotenv_files() -> None:
    """
    Load env files from backend root (if available).

    Order:
    - .env (defaults, not committed)
    - .env.local (developer overrides, not committed)
    - .env.example (repo defaults fallback)
    """
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return

    root = _backend_root()
    # Do not override real environment variables.
    load_dotenv(root / ".env", override=False)
    load_dotenv(root / ".env.local", override=True)
    # Fallback so developers can run without creating .env initially.
    load_dotenv(root / ".env.example", override=False)


def _default_sqlite_path(*, app_name: str = "agent-team") -> Path:
    _load_dotenv_files()

    override = os.environ.get("STORE_SQLITE_PATH")
    if override:
        path = Path(override).expanduser()
        if not path.is_absolute():
            path = (_backend_root() / path).resolve()
        return path

    platform = os.sys.platform
    if platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))

    return base / app_name / "app.db"


def _json_default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _try_parse_datetime(value: str) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        # Handle Zulu suffix if present.
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _restore_datetimes(obj: Any) -> Any:
    if isinstance(obj, list):
        return [_restore_datetimes(v) for v in obj]
    if isinstance(obj, dict):
        restored: dict[str, Any] = {}
        for k, v in obj.items():
            if k in {"created_at", "updated_at", "started_at", "completed_at"} and isinstance(v, str):
                dt = _try_parse_datetime(v)
                restored[k] = dt if dt is not None else v
            else:
                restored[k] = _restore_datetimes(v)
        return restored
    return obj


class SQLiteKV:
    """
    Minimal SQLite persistence for JSON records keyed by `id`.

    This is intentionally small and only used for user settings-like entities
    (agents, teams, model_configs).
    """

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
            self._conn.execute("PRAGMA foreign_keys=ON;")
            self._conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);")
            cur = self._conn.execute("SELECT version FROM schema_version LIMIT 1;")
            row = cur.fetchone()
            if row is None:
                self._conn.execute("INSERT INTO schema_version(version) VALUES (1);")

            for table in ("agents", "teams", "model_configs"):
                self._conn.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {table} (
                        id TEXT PRIMARY KEY,
                        data_json TEXT NOT NULL,
                        created_at TEXT,
                        updated_at TEXT
                    );
                    """
                )

    def list(self, table: str) -> list[dict[str, Any]]:
        with self._lock, self._conn:
            rows = self._conn.execute(f"SELECT id, data_json FROM {table};").fetchall()
        records: list[dict[str, Any]] = []
        for row in rows:
            data = json.loads(row["data_json"])
            records.append(_restore_datetimes(data))
        return records

    def upsert(self, table: str, record: dict[str, Any]) -> None:
        record_id = record.get("id")
        if not record_id:
            raise ValueError("record.id is required")

        payload = json.dumps(record, ensure_ascii=False, default=_json_default)
        created_at = record.get("created_at")
        updated_at = record.get("updated_at")
        created_at_s = created_at.isoformat() if isinstance(created_at, datetime) else (created_at or None)
        updated_at_s = updated_at.isoformat() if isinstance(updated_at, datetime) else (updated_at or None)

        with self._lock, self._conn:
            self._conn.execute(
                f"""
                INSERT INTO {table}(id, data_json, created_at, updated_at)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    data_json=excluded.data_json,
                    updated_at=excluded.updated_at;
                """,
                (record_id, payload, created_at_s, updated_at_s),
            )
            self._conn.commit()

    def delete(self, table: str, record_id: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(f"DELETE FROM {table} WHERE id=?;", (record_id,))
            self._conn.commit()


@dataclass
class Store:
    agents: dict[str, dict[str, Any]] = field(default_factory=dict)
    teams: dict[str, dict[str, Any]] = field(default_factory=dict)
    executions: dict[str, dict[str, Any]] = field(default_factory=dict)
    execution_messages: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    model_configs: dict[str, dict[str, Any]] = field(default_factory=dict)
    _sqlite: Optional[SQLiteKV] = field(default=None, init=False, repr=False)

    def new_id(self) -> str:
        return str(uuid4())

    def touch(self, record: dict[str, Any], *, created: bool = False) -> None:
        now = utcnow()
        if created:
            record["created_at"] = now
        record["updated_at"] = now

    def enable_sqlite(self, path: Optional[Path] = None) -> None:
        if self._sqlite is not None:
            return

        db_path = path or _default_sqlite_path()
        self._sqlite = SQLiteKV(db_path)

        # Load persisted settings-like entities into memory.
        self.agents = {r["id"]: r for r in self._sqlite.list("agents")}
        self.teams = {r["id"]: r for r in self._sqlite.list("teams")}
        self.model_configs = {r["id"]: r for r in self._sqlite.list("model_configs")}

    def upsert_agent(self, record: dict[str, Any]) -> None:
        self.agents[record["id"]] = record
        if self._sqlite is not None:
            self._sqlite.upsert("agents", record)

    def delete_agent(self, agent_id: str) -> None:
        self.agents.pop(agent_id, None)
        if self._sqlite is not None:
            self._sqlite.delete("agents", agent_id)

    def upsert_team(self, record: dict[str, Any]) -> None:
        self.teams[record["id"]] = record
        if self._sqlite is not None:
            self._sqlite.upsert("teams", record)

    def delete_team(self, team_id: str) -> None:
        self.teams.pop(team_id, None)
        if self._sqlite is not None:
            self._sqlite.delete("teams", team_id)

    def upsert_model_config(self, record: dict[str, Any]) -> None:
        self.model_configs[record["id"]] = record
        if self._sqlite is not None:
            self._sqlite.upsert("model_configs", record)

    def delete_model_config(self, config_id: str) -> None:
        self.model_configs.pop(config_id, None)
        if self._sqlite is not None:
            self._sqlite.delete("model_configs", config_id)


_store: Optional[Store] = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store()
        backend = (os.environ.get("STORE_BACKEND") or "sqlite").strip().lower()
        if backend in {"sqlite", "sqlite3"}:
            _store.enable_sqlite()
    return _store
