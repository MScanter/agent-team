"""
Shared state manager for orchestration.
"""

from typing import Any, Optional
from dataclasses import dataclass, field
import json


@dataclass
class SharedStateManager:
    """
    Manages shared state between agents during orchestration.

    Provides thread-safe access to shared discussion state.
    """

    _state: dict = field(default_factory=dict)
    _history: list[dict] = field(default_factory=list)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from shared state."""
        return self._state.get(key, default)

    def set(self, key: str, value: Any, record_history: bool = True):
        """Set a value in shared state."""
        if record_history:
            self._history.append({
                "action": "set",
                "key": key,
                "old_value": self._state.get(key),
                "new_value": value,
            })
        self._state[key] = value

    def update(self, data: dict, record_history: bool = True):
        """Update multiple values in shared state."""
        if record_history:
            for key, value in data.items():
                self._history.append({
                    "action": "set",
                    "key": key,
                    "old_value": self._state.get(key),
                    "new_value": value,
                })
        self._state.update(data)

    def delete(self, key: str):
        """Delete a key from shared state."""
        if key in self._state:
            self._history.append({
                "action": "delete",
                "key": key,
                "old_value": self._state.get(key),
            })
            del self._state[key]

    def clear(self):
        """Clear all shared state."""
        self._history.append({
            "action": "clear",
            "old_state": self._state.copy(),
        })
        self._state.clear()

    def get_all(self) -> dict:
        """Get entire shared state."""
        return self._state.copy()

    def get_history(self) -> list[dict]:
        """Get state change history."""
        return self._history.copy()

    def to_json(self) -> str:
        """Serialize state to JSON."""
        return json.dumps(self._state, ensure_ascii=False, default=str)

    @classmethod
    def from_json(cls, json_str: str) -> "SharedStateManager":
        """Create from JSON string."""
        manager = cls()
        manager._state = json.loads(json_str)
        return manager

    # Convenience methods for common state operations

    def add_opinion(self, agent_id: str, agent_name: str, content: str, metadata: dict = None):
        """Add an opinion to the opinions list."""
        opinions = self.get("opinions", [])
        opinions.append({
            "agent_id": agent_id,
            "agent_name": agent_name,
            "content": content,
            "metadata": metadata or {},
        })
        self.set("opinions", opinions)

    def get_opinions(self, agent_id: Optional[str] = None) -> list[dict]:
        """Get opinions, optionally filtered by agent."""
        opinions = self.get("opinions", [])
        if agent_id:
            return [op for op in opinions if op["agent_id"] == agent_id]
        return opinions

    def set_agent_status(self, agent_id: str, status: str, metadata: dict = None):
        """Set status for an agent."""
        agent_states = self.get("agent_states", {})
        agent_states[agent_id] = {
            "status": status,
            **(metadata or {}),
        }
        self.set("agent_states", agent_states)

    def get_agent_status(self, agent_id: str) -> Optional[dict]:
        """Get status for an agent."""
        return self.get("agent_states", {}).get(agent_id)

    def increment_round(self) -> int:
        """Increment and return the current round number."""
        current_round = self.get("round", 0) + 1
        self.set("round", current_round)
        return current_round

    def add_to_budget_used(self, tokens: int, cost: float = 0.0):
        """Add to budget usage tracking."""
        self.set("tokens_used", self.get("tokens_used", 0) + tokens)
        self.set("cost_used", self.get("cost_used", 0.0) + cost)
