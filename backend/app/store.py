"""
In-memory application store (single-user, no database).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4


def utcnow() -> datetime:
    return datetime.utcnow()


LOCAL_USER_ID = "local"


@dataclass
class Store:
    agents: dict[str, dict[str, Any]] = field(default_factory=dict)
    teams: dict[str, dict[str, Any]] = field(default_factory=dict)
    executions: dict[str, dict[str, Any]] = field(default_factory=dict)
    execution_messages: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    model_configs: dict[str, dict[str, Any]] = field(default_factory=dict)

    def new_id(self) -> str:
        return str(uuid4())

    def touch(self, record: dict[str, Any], *, created: bool = False) -> None:
        now = utcnow()
        if created:
            record["created_at"] = now
        record["updated_at"] = now


_store: Optional[Store] = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store()
    return _store

