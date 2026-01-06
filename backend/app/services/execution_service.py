"""
Execution service backed by the in-memory Store (single-user, no database).
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Optional

from app.agents.base import AgentConfig, AgentInstance
from app.orchestration import (
    OrchestrationState,
    OrchestrationEvent,
    RoundtableOrchestrator,
    PipelineOrchestrator,
    DebateOrchestrator,
    CustomOrchestrator,
)
from app.schemas.execution import ExecutionCreate, BudgetConfig
from app.services.llm_service import get_provider_for_agent
from app.store import Store, LOCAL_USER_ID, utcnow


class ExecutionService:
    """Service for execution management and orchestration."""

    def __init__(self, store: Store):
        self.store = store

    def list(
        self,
        user_id: str = LOCAL_USER_ID,
        page: int = 1,
        page_size: int = 20,
        team_id: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> tuple[list[dict], int]:
        executions = [e for e in self.store.executions.values() if e.get("user_id") == user_id]

        if team_id:
            executions = [e for e in executions if e.get("team_id") == team_id]

        if status_filter:
            executions = [e for e in executions if e.get("status") == status_filter]

        executions.sort(key=lambda e: e.get("created_at"), reverse=True)
        total = len(executions)
        start = (page - 1) * page_size
        end = start + page_size
        return executions[start:end], total

    def get(self, execution_id: str, user_id: Optional[str] = LOCAL_USER_ID) -> Optional[dict]:
        execution = self.store.executions.get(execution_id)
        if not execution:
            return None
        if user_id and execution.get("user_id") != user_id:
            return None
        return execution

    def get_messages(
        self,
        execution_id: str,
        limit: int = 100,
        offset: int = 0,
        round_filter: Optional[int] = None,
        agent_id: Optional[str] = None,
    ) -> list[dict]:
        messages = list(self.store.execution_messages.get(execution_id) or [])

        if round_filter is not None:
            messages = [m for m in messages if m.get("round") == round_filter]

        if agent_id:
            messages = [m for m in messages if m.get("sender_id") == agent_id]

        messages.sort(key=lambda m: m.get("sequence", 0))
        return messages[offset : offset + limit]

    def create(self, user_id: str, data: ExecutionCreate) -> dict:
        if data.team_id not in self.store.teams:
            raise ValueError("Team not found")

        budget = data.budget or BudgetConfig()
        execution_id = self.store.new_id()
        record = {
            "id": execution_id,
            "user_id": user_id,
            "team_id": data.team_id,
            "title": data.title,
            "initial_input": data.input or "",
            "llm": data.llm.model_dump() if data.llm else None,
            "status": "pending",
            "current_stage": None,
            "current_round": 0,
            "shared_state": {},
            "agent_states": {},
            "final_output": None,
            "structured_output": None,
            "tokens_used": 0,
            "tokens_budget": budget.max_tokens,
            "cost": 0.0,
            "cost_budget": budget.max_cost,
            "started_at": None,
            "completed_at": None,
            "error_message": None,
            "retry_count": 0,
        }
        self.store.touch(record, created=True)
        self.store.executions[execution_id] = record
        self.store.execution_messages[execution_id] = []
        return record

    async def start(self, execution_id: str, user_id: str) -> AsyncIterator[OrchestrationEvent]:
        execution = self.get(execution_id, user_id)
        if not execution:
            yield OrchestrationEvent(event_type="error", data={"message": "Execution not found"}, sequence=0)
            return

        if execution.get("status") != "pending":
            yield OrchestrationEvent(
                event_type="error",
                data={"message": f"Cannot start execution in {execution.get('status')} status"},
                sequence=0,
            )
            return

        team = self.store.teams.get(execution.get("team_id"))
        if not team:
            yield OrchestrationEvent(event_type="error", data={"message": "Team not found"}, sequence=0)
            return

        members = [m for m in (team.get("members") or []) if m.get("is_active")]
        members.sort(key=lambda m: m.get("position", 0))
        agent_ids = [m.get("agent_id") for m in members]
        agent_records = [self.store.agents.get(agent_id) for agent_id in agent_ids if self.store.agents.get(agent_id)]
        if not agent_records:
            yield OrchestrationEvent(event_type="error", data={"message": "No agents in team"}, sequence=0)
            return

        llm_config = execution.get("llm") or None
        try:
            agent_instances: list[AgentInstance] = []
            for agent in agent_records:
                interaction_rules = agent.get("interaction_rules") or {}
                config = AgentConfig(
                    id=agent["id"],
                    name=agent["name"],
                    system_prompt=agent["system_prompt"],
                    model_id=agent.get("model_id"),
                    temperature=agent.get("temperature", 0.7),
                    max_tokens=agent.get("max_tokens", 2048),
                    domain=agent.get("domain"),
                    collaboration_style=agent.get("collaboration_style", "supportive"),
                    speaking_priority=agent.get("speaking_priority", 5),
                    can_challenge=interaction_rules.get("can_challenge", True),
                    can_be_challenged=interaction_rules.get("can_be_challenged", True),
                    defer_to=interaction_rules.get("defer_to", []),
                    tools=agent.get("tools") or [],
                    memory_enabled=bool(agent.get("memory_enabled")),
                    avatar=agent.get("avatar"),
                    description=agent.get("description"),
                )
                provider = await get_provider_for_agent(self.store, agent, llm_config=llm_config)
                agent_instances.append(AgentInstance(config=config, llm_provider=provider))
        except Exception as e:
            yield OrchestrationEvent(event_type="error", data={"message": str(e)}, sequence=0)
            return

        execution["status"] = "running"
        execution["started_at"] = utcnow()
        self.store.touch(execution)

        state = OrchestrationState(
            topic=execution["initial_input"],
            tokens_budget=execution["tokens_budget"],
            cost_budget=execution["cost_budget"],
        )
        coordinator_llm = None
        if llm_config and llm_config.get("default"):
            from app.services.llm_service import get_provider_for_model_config

            coordinator_llm = await get_provider_for_model_config(llm_config["default"])

        orchestrator = self._get_orchestrator(
            team.get("collaboration_mode") or "roundtable",
            team.get("mode_config") or {},
            coordinator_llm=coordinator_llm,
        )

        sequence = 0
        final_output: Optional[str] = None
        gen = orchestrator.run(agent_instances, state)
        try:
            async for event in gen:
                # Honor pause/stop control at event boundaries.
                if execution.get("status") == "completed":
                    break
                if execution.get("status") == "paused":
                    sequence += 1
                    yield OrchestrationEvent(
                        event_type="status",
                        data={"message": "Paused", "phase": "paused"},
                        sequence=sequence,
                    )
                    while execution.get("status") == "paused":
                        await asyncio.sleep(0.25)
                    if execution.get("status") == "completed":
                        break
                    sequence += 1
                    yield OrchestrationEvent(
                        event_type="status",
                        data={"message": "Resumed", "phase": "resumed"},
                        sequence=sequence,
                    )

                sequence += 1
                event.sequence = sequence

                if event.event_type == "done":
                    final_output = (event.data or {}).get("final_output") or (event.data or {}).get("final_summary")

                self._save_message(execution_id, event, state.round)

                execution["current_round"] = state.round
                execution["tokens_used"] = state.tokens_used
                execution["cost"] = state.cost
                execution["shared_state"] = state.to_dict()
                self.store.touch(execution)

                yield event

            # If stopped by user, keep status as-is (control endpoint sets it).
            if execution.get("status") != "failed":
                if execution.get("status") != "completed":
                    execution["status"] = "completed"
                    execution["completed_at"] = utcnow()
                execution["final_output"] = execution.get("final_output") or final_output or state.summary
                self.store.touch(execution)

        except Exception as e:
            execution["status"] = "failed"
            execution["error_message"] = str(e)
            self.store.touch(execution)
            yield OrchestrationEvent(event_type="error", data={"message": str(e)}, sequence=sequence + 1)
        finally:
            try:
                await gen.aclose()
            except Exception:
                pass

    async def followup(
        self,
        execution_id: str,
        user_id: str,
        input_text: str,
        target_agent_id: Optional[str] = None,
    ) -> AsyncIterator[OrchestrationEvent]:
        execution = self.get(execution_id, user_id)
        if not execution or execution.get("status") not in ("paused", "completed"):
            yield OrchestrationEvent(event_type="error", data={"message": "Invalid execution"}, sequence=0)
            return

        team = self.store.teams.get(execution.get("team_id"))
        if not team:
            yield OrchestrationEvent(event_type="error", data={"message": "Team not found"}, sequence=0)
            return

        members = [m for m in (team.get("members") or []) if m.get("is_active")]
        members.sort(key=lambda m: m.get("position", 0))
        agent_ids = [m.get("agent_id") for m in members]
        agent_records = [self.store.agents.get(agent_id) for agent_id in agent_ids if self.store.agents.get(agent_id)]
        if not agent_records:
            yield OrchestrationEvent(event_type="error", data={"message": "No agents in team"}, sequence=0)
            return

        llm_config = execution.get("llm") or None
        agent_instances: list[AgentInstance] = []
        for agent in agent_records:
            interaction_rules = agent.get("interaction_rules") or {}
            config = AgentConfig(
                id=agent["id"],
                name=agent["name"],
                system_prompt=agent["system_prompt"],
                model_id=agent.get("model_id"),
                temperature=agent.get("temperature", 0.7),
                max_tokens=agent.get("max_tokens", 2048),
                domain=agent.get("domain"),
                collaboration_style=agent.get("collaboration_style", "supportive"),
                speaking_priority=agent.get("speaking_priority", 5),
                can_challenge=interaction_rules.get("can_challenge", True),
                can_be_challenged=interaction_rules.get("can_be_challenged", True),
                defer_to=interaction_rules.get("defer_to", []),
                tools=agent.get("tools") or [],
                memory_enabled=bool(agent.get("memory_enabled")),
                avatar=agent.get("avatar"),
                description=agent.get("description"),
            )
            provider = await get_provider_for_agent(self.store, agent, llm_config=llm_config)
            agent_instances.append(AgentInstance(config=config, llm_provider=provider))

        execution["status"] = "running"
        self.store.touch(execution)

        state = OrchestrationState(
            topic=input_text,
            round=execution.get("current_round", 0),
            tokens_used=execution.get("tokens_used", 0),
            tokens_budget=execution.get("tokens_budget", 200000),
            cost=execution.get("cost", 0.0),
            cost_budget=execution.get("cost_budget", 10.0),
            summary=(execution.get("shared_state") or {}).get("summary", ""),
        )
        coordinator_llm = None
        if llm_config and llm_config.get("default"):
            from app.services.llm_service import get_provider_for_model_config

            coordinator_llm = await get_provider_for_model_config(llm_config["default"])

        orchestrator = self._get_orchestrator(
            team.get("collaboration_mode") or "roundtable",
            team.get("mode_config") or {},
            coordinator_llm=coordinator_llm,
        )

        sequence = 0
        final_output: Optional[str] = None
        try:
            async for event in orchestrator.handle_followup(input_text, agent_instances, state, target_agent_id):
                sequence += 1
                event.sequence = sequence

                if event.event_type == "done":
                    final_output = (event.data or {}).get("final_output") or (event.data or {}).get("final_summary")

                self._save_message(execution_id, event, state.round)

                execution["current_round"] = state.round
                execution["tokens_used"] = state.tokens_used
                execution["cost"] = state.cost
                execution["shared_state"] = state.to_dict()
                self.store.touch(execution)

                yield event

            execution["status"] = "completed"
            if final_output:
                execution["final_output"] = final_output
            self.store.touch(execution)

        except Exception as e:
            execution["status"] = "failed"
            execution["error_message"] = str(e)
            self.store.touch(execution)
            yield OrchestrationEvent(event_type="error", data={"message": str(e)}, sequence=sequence + 1)

    def control(self, execution_id: str, user_id: str, action: str, params: Optional[dict] = None) -> bool:
        execution = self.get(execution_id, user_id)
        if not execution:
            return False

        params = params or {}
        status = execution.get("status")

        if action == "pause" and status == "running":
            execution["status"] = "paused"
        elif action == "resume" and status == "paused":
            execution["status"] = "running"
        elif action == "stop" and status in ("running", "paused"):
            execution["status"] = "completed"
            execution["completed_at"] = utcnow()
        elif action == "extend_budget":
            execution["tokens_budget"] = int(execution.get("tokens_budget") or 0) + int(params.get("tokens", 50000))
            execution["cost_budget"] = float(execution.get("cost_budget") or 0) + float(params.get("cost", 5.0))
        else:
            return False

        self.store.touch(execution)
        return True

    def delete(self, execution_id: str, user_id: str) -> bool:
        execution = self.get(execution_id, user_id)
        if not execution:
            return False
        self.store.executions.pop(execution_id, None)
        self.store.execution_messages.pop(execution_id, None)
        return True

    def _get_orchestrator(self, mode: str, config: dict, coordinator_llm=None):
        if mode == "pipeline":
            return PipelineOrchestrator(config)
        if mode == "debate":
            return DebateOrchestrator(config)
        if mode == "custom":
            return CustomOrchestrator(config)
        return RoundtableOrchestrator(config, coordinator_llm=coordinator_llm)

    def _save_message(self, execution_id: str, event: OrchestrationEvent, round_num: int) -> None:
        if event.event_type not in ("opinion", "summary", "done"):
            return

        messages = self.store.execution_messages.setdefault(execution_id, [])
        max_seq = max((m.get("sequence", 0) for m in messages), default=0)

        data = event.data or {}
        content = (
            data.get("content")
            or data.get("summary")
            or data.get("final_summary")
            or data.get("final_output")
            or ""
        )
        msg = {
            "id": self.store.new_id(),
            "sequence": max_seq + 1,
            "round": round_num,
            "phase": data.get("phase") or event.event_type,
            "sender_type": "agent" if event.agent_id else "system",
            "sender_id": event.agent_id,
            "sender_name": data.get("agent_name"),
            "content": content,
            "content_type": "text",
            "responding_to": data.get("responding_to"),
            "target_agent_id": data.get("target_agent_id"),
            "confidence": data.get("confidence"),
            "wants_to_continue": data.get("wants_to_continue", True),
            "input_tokens": data.get("input_tokens", 0),
            "output_tokens": data.get("output_tokens", 0),
            "message_metadata": data.get("metadata", {}),
        }
        self.store.touch(msg, created=True)
        messages.append(msg)
