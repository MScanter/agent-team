"""
Team service backed by the in-memory Store (single-user, no database).
"""

from __future__ import annotations

from typing import Optional

from app.schemas.team import TeamCreate, TeamUpdate, TeamMemberCreate
from app.store import Store, LOCAL_USER_ID


class TeamService:
    """Service for team CRUD operations."""

    def __init__(self, store: Store):
        self.store = store

    def list(
        self,
        user_id: str = LOCAL_USER_ID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        collaboration_mode: Optional[str] = None,
        is_template: Optional[bool] = None,
        include_public: bool = True,
    ) -> tuple[list[dict], int]:
        teams = list(self.store.teams.values())

        if user_id:
            if include_public:
                teams = [t for t in teams if t.get("user_id") == user_id or t.get("is_public") is True]
            else:
                teams = [t for t in teams if t.get("user_id") == user_id]

        if search:
            needle = search.lower()
            teams = [
                t
                for t in teams
                if needle in (t.get("name") or "").lower()
                or needle in (t.get("description") or "").lower()
            ]

        if collaboration_mode:
            teams = [t for t in teams if t.get("collaboration_mode") == collaboration_mode]

        if is_template is not None:
            teams = [t for t in teams if t.get("is_template") is is_template]

        teams.sort(key=lambda t: t.get("updated_at"), reverse=True)
        total = len(teams)
        start = (page - 1) * page_size
        end = start + page_size
        return teams[start:end], total

    def get(self, team_id: str, user_id: Optional[str] = LOCAL_USER_ID) -> Optional[dict]:
        team = self.store.teams.get(team_id)
        if not team:
            return None
        if user_id and team.get("user_id") != user_id and not team.get("is_public"):
            return None
        return team

    def create(self, user_id: str, data: TeamCreate) -> dict:
        team_id = self.store.new_id()
        members: list[dict] = []
        for i, member_data in enumerate(data.members or []):
            position = member_data.position if member_data.position is not None else i
            record = {
                "id": self.store.new_id(),
                "agent_id": member_data.agent_id,
                "role_override": member_data.role_override,
                "priority_override": member_data.priority_override,
                "config_override": member_data.config_override or {},
                "position": position,
                "is_active": True,
            }
            self.store.touch(record, created=True)
            members.append(record)

        members.sort(key=lambda m: m.get("position", 0))

        record = {
            "id": team_id,
            "user_id": user_id,
            "name": data.name,
            "description": data.description,
            "icon": data.icon,
            "collaboration_mode": data.collaboration_mode,
            "mode_config": data.mode_config or {},
            "coordinator_id": data.coordinator_id,
            "coordination_rules": data.coordination_rules.model_dump() if data.coordination_rules else {},
            "output_rules": data.output_rules.model_dump() if data.output_rules else {},
            "is_template": data.is_template,
            "is_public": data.is_public,
            "usage_count": 0,
            "rating": 0.0,
            "rating_count": 0,
            "members": members,
        }
        self.store.touch(record, created=True)
        self.store.teams[team_id] = record
        return record

    def update(self, team_id: str, user_id: str, data: TeamUpdate) -> Optional[dict]:
        team = self.get(team_id, user_id)
        if not team or team.get("user_id") != user_id:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if "coordination_rules" in update_data and update_data["coordination_rules"] is not None:
            update_data["coordination_rules"] = update_data["coordination_rules"].model_dump()
        if "output_rules" in update_data and update_data["output_rules"] is not None:
            update_data["output_rules"] = update_data["output_rules"].model_dump()

        for field, value in update_data.items():
            team[field] = value

        self.store.touch(team)
        return team

    def delete(self, team_id: str, user_id: str) -> bool:
        team = self.get(team_id, user_id)
        if not team or team.get("user_id") != user_id:
            return False
        self.store.teams.pop(team_id, None)
        return True

    def add_member(self, team_id: str, user_id: str, data: TeamMemberCreate) -> Optional[dict]:
        team = self.get(team_id, user_id)
        if not team or team.get("user_id") != user_id:
            return None

        # Ensure agent exists (single-user store).
        if data.agent_id not in self.store.agents:
            return None

        members: list[dict] = team.get("members") or []
        existing = next((m for m in members if m.get("agent_id") == data.agent_id), None)
        if existing:
            return existing

        max_pos = max((m.get("position", 0) for m in members), default=-1)
        member_id = self.store.new_id()
        record = {
            "id": member_id,
            "agent_id": data.agent_id,
            "role_override": data.role_override,
            "priority_override": data.priority_override,
            "config_override": data.config_override or {},
            "position": data.position if data.position is not None else max_pos + 1,
            "is_active": True,
        }
        self.store.touch(record, created=True)
        members.append(record)
        members.sort(key=lambda m: m.get("position", 0))
        team["members"] = members
        self.store.touch(team)
        return record

    def remove_member(self, team_id: str, agent_id: str, user_id: str) -> bool:
        team = self.get(team_id, user_id)
        if not team or team.get("user_id") != user_id:
            return False

        members: list[dict] = team.get("members") or []
        before = len(members)
        members = [m for m in members if m.get("agent_id") != agent_id]
        if len(members) == before:
            return False
        team["members"] = members
        self.store.touch(team)
        return True

    def reorder_members(self, team_id: str, user_id: str, agent_ids: list[str]) -> bool:
        team = self.get(team_id, user_id)
        if not team or team.get("user_id") != user_id:
            return False

        if len(set(agent_ids)) != len(agent_ids):
            raise ValueError("agent_ids contains duplicates")

        members: list[dict] = team.get("members") or []
        members_by_agent_id = {m.get("agent_id"): m for m in members}
        missing = [agent_id for agent_id in agent_ids if agent_id not in members_by_agent_id]
        if missing:
            raise ValueError(f"Unknown agent_ids in team: {', '.join(missing)}")

        remaining = [m.get("agent_id") for m in sorted(members, key=lambda m: m.get("position", 0)) if m.get("agent_id") not in agent_ids]
        ordered = list(agent_ids) + remaining
        for i, agent_id in enumerate(ordered):
            members_by_agent_id[agent_id]["position"] = i

        team["members"] = sorted(members, key=lambda m: m.get("position", 0))
        self.store.touch(team)
        return True

    def duplicate(self, team_id: str, user_id: str, new_name: Optional[str] = None) -> Optional[dict]:
        original = self.get(team_id, user_id)
        if not original:
            return None

        new_id = self.store.new_id()
        members_copy = []
        for m in original.get("members") or []:
            member = {k: v for k, v in m.items() if k not in ("id", "created_at", "updated_at")}
            member["id"] = self.store.new_id()
            self.store.touch(member, created=True)
            members_copy.append(member)

        record = {
            **{k: v for k, v in original.items() if k not in ("id", "created_at", "updated_at", "members")},
            "id": new_id,
            "user_id": user_id,
            "name": new_name or f"{original.get('name')} (副本)",
            "is_template": False,
            "is_public": False,
            "usage_count": 0,
            "rating": 0.0,
            "rating_count": 0,
            "members": sorted(members_copy, key=lambda m: m.get("position", 0)),
        }
        self.store.touch(record, created=True)
        self.store.teams[new_id] = record
        return record

    def increment_usage(self, team_id: str) -> None:
        team = self.get(team_id, user_id=None)
        if not team:
            return
        team["usage_count"] = int(team.get("usage_count") or 0) + 1
        self.store.touch(team)
