"""
Agent service backed by the in-memory Store (single-user, no database).
"""

from __future__ import annotations

from typing import Optional

from app.schemas.agent import AgentCreate, AgentUpdate
from app.store import Store, LOCAL_USER_ID


class AgentService:
    """Service for agent CRUD operations."""

    def __init__(self, store: Store):
        self.store = store

    def list(
        self,
        user_id: str = LOCAL_USER_ID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        tags: Optional[list[str]] = None,
        is_template: Optional[bool] = None,
        collaboration_style: Optional[str] = None,
        include_public: bool = True,
    ) -> tuple[list[dict], int]:
        agents = list(self.store.agents.values())

        if user_id:
            if include_public:
                agents = [a for a in agents if a.get("user_id") == user_id or a.get("is_public") is True]
            else:
                agents = [a for a in agents if a.get("user_id") == user_id]

        if search:
            needle = search.lower()
            agents = [
                a
                for a in agents
                if needle in (a.get("name") or "").lower()
                or needle in (a.get("description") or "").lower()
            ]

        if tags:
            tag_set = set(tags)
            agents = [a for a in agents if tag_set.intersection(set(a.get("tags") or []))]

        if is_template is not None:
            agents = [a for a in agents if a.get("is_template") is is_template]

        if collaboration_style:
            agents = [a for a in agents if a.get("collaboration_style") == collaboration_style]

        agents.sort(key=lambda a: a.get("updated_at"), reverse=True)
        total = len(agents)
        start = (page - 1) * page_size
        end = start + page_size
        return agents[start:end], total

    def get(self, agent_id: str, user_id: Optional[str] = LOCAL_USER_ID) -> Optional[dict]:
        agent = self.store.agents.get(agent_id)
        if not agent:
            return None
        if user_id and agent.get("user_id") != user_id and not agent.get("is_public"):
            return None
        return agent

    def create(self, user_id: str, data: AgentCreate) -> dict:
        agent_id = self.store.new_id()
        record = {
            "id": agent_id,
            "user_id": user_id,
            "name": data.name,
            "avatar": data.avatar,
            "description": data.description,
            "tags": data.tags or [],
            "system_prompt": data.system_prompt,
            "model_id": data.model_id,
            "temperature": data.temperature,
            "max_tokens": data.max_tokens,
            "tools": data.tools or [],
            "knowledge_base_id": data.knowledge_base_id,
            "memory_enabled": data.memory_enabled,
            "domain": data.domain,
            "collaboration_style": data.collaboration_style,
            "speaking_priority": data.speaking_priority,
            "interaction_rules": data.interaction_rules.model_dump() if data.interaction_rules else {},
            "version": 1,
            "is_template": data.is_template,
            "is_public": data.is_public,
            "parent_id": None,
            "usage_count": 0,
            "rating": 0.0,
            "rating_count": 0,
        }
        self.store.touch(record, created=True)
        self.store.agents[agent_id] = record
        return record

    def update(self, agent_id: str, user_id: str, data: AgentUpdate) -> Optional[dict]:
        agent = self.get(agent_id, user_id)
        if not agent or agent.get("user_id") != user_id:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "interaction_rules" in update_data and update_data["interaction_rules"] is not None:
            update_data["interaction_rules"] = update_data["interaction_rules"].model_dump()

        for field, value in update_data.items():
            agent[field] = value

        agent["version"] = int(agent.get("version") or 1) + 1
        self.store.touch(agent)
        return agent

    def delete(self, agent_id: str, user_id: str) -> bool:
        agent = self.get(agent_id, user_id)
        if not agent or agent.get("user_id") != user_id:
            return False
        self.store.agents.pop(agent_id, None)
        return True

    def duplicate(self, agent_id: str, user_id: str, new_name: Optional[str] = None) -> Optional[dict]:
        original = self.get(agent_id, user_id)
        if not original:
            return None

        new_id = self.store.new_id()
        record = {
            **{k: v for k, v in original.items() if k not in ("id", "created_at", "updated_at")},
            "id": new_id,
            "user_id": user_id,
            "name": new_name or f"{original.get('name')} (副本)",
            "is_template": False,
            "is_public": False,
            "parent_id": original["id"],
            "version": 1,
            "usage_count": 0,
            "rating": 0.0,
            "rating_count": 0,
        }
        self.store.touch(record, created=True)
        self.store.agents[new_id] = record
        return record

    def get_templates(self, category: Optional[str] = None) -> list[dict]:
        templates = [a for a in self.store.agents.values() if a.get("is_template") is True]
        if category:
            templates = [t for t in templates if t.get("domain") == category]
        templates.sort(key=lambda a: a.get("usage_count", 0), reverse=True)
        return templates

    def create_from_template(
        self,
        template_id: str,
        user_id: str,
        name: str,
        customizations: Optional[AgentUpdate] = None,
    ) -> Optional[dict]:
        template = self.get(template_id, user_id=None)
        if not template or not template.get("is_template"):
            return None

        agent = self.duplicate(template_id, user_id, name)
        if not agent:
            return None

        if customizations:
            updated = self.update(agent["id"], user_id, customizations)
            if updated:
                agent = updated

        template["usage_count"] = int(template.get("usage_count") or 0) + 1
        self.store.touch(template)
        return agent

    def increment_usage(self, agent_id: str) -> None:
        agent = self.get(agent_id, user_id=None)
        if not agent:
            return
        agent["usage_count"] = int(agent.get("usage_count") or 0) + 1
        self.store.touch(agent)
