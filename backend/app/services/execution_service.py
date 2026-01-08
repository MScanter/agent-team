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
    OrchestrationPhase,
    Opinion,
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
        self.store.upsert_execution(record)
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

        initial_input = (execution.get("initial_input") or "").strip()
        if not initial_input:
            execution["status"] = "paused"
            self.store.touch(execution)
            yield OrchestrationEvent(
                event_type="status",
                data={
                    "message": "等待输入讨论主题（请输入内容后发送追问以继续）",
                    "phase": "awaiting_user_input",
                },
                sequence=1,
            )
            return

        team = self.store.teams.get(execution.get("team_id"))
        if not team:
            yield OrchestrationEvent(event_type="error", data={"message": "Team not found"}, sequence=0)
            return

        llm_config = execution.get("llm") or None
        try:
            agent_instances = await self._build_agent_instances(team, llm_config)
        except Exception as e:
            yield OrchestrationEvent(event_type="error", data={"message": str(e)}, sequence=0)
            return

        execution["status"] = "running"
        execution["started_at"] = utcnow()
        self.store.touch(execution)
        self.store.upsert_execution(execution)

        state = self._build_state_from_execution(execution, topic=initial_input)
        state.start_new_round()
        sequence = 0
        try:
            user_msg = self._save_user_message(execution_id, initial_input, state.round)
            sequence += 1
            yield OrchestrationEvent(
                event_type="user",
                data={
                    "content": initial_input,
                    "phase": "user",
                    "round": state.round,
                    "message_id": user_msg["id"],
                    "message_sequence": user_msg["sequence"],
                },
                sequence=sequence,
            )

            recent_context = self._recent_opinions(state, limit=6)
            async for event in self._run_round(
                execution_id,
                agent_instances,
                state,
                phase="initial",
                recent_opinions=recent_context,
                sequence=sequence,
            ):
                sequence = event.sequence
                self._update_execution_state(execution, state)
                yield event
            round_one = list(state.current_round_opinions)

            async for event in self._run_round(
                execution_id,
                agent_instances,
                state,
                phase="response",
                recent_opinions=[self._opinion_to_dict(op) for op in round_one],
                sequence=sequence,
            ):
                sequence = event.sequence
                self._update_execution_state(execution, state)
                yield event

            execution["status"] = "completed"
            execution["completed_at"] = utcnow()
            execution["current_round"] = state.round
            execution["tokens_used"] = state.tokens_used
            execution["cost"] = state.cost
            execution["shared_state"] = state.to_dict()
            self.store.touch(execution)
            self.store.upsert_execution(execution)

            sequence += 1
            yield OrchestrationEvent(
                event_type="status",
                data={"status": "completed"},
                sequence=sequence,
            )

        except Exception as e:
            execution["status"] = "failed"
            execution["error_message"] = str(e)
            self.store.touch(execution)
            self.store.upsert_execution(execution)
            yield OrchestrationEvent(event_type="error", data={"message": str(e)}, sequence=sequence + 1)

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

        llm_config = execution.get("llm") or None
        try:
            agent_instances = await self._build_agent_instances(team, llm_config)
        except Exception as e:
            yield OrchestrationEvent(event_type="error", data={"message": str(e)}, sequence=0)
            return

        execution["status"] = "running"
        self.store.touch(execution)
        self.store.upsert_execution(execution)

        base_topic = self._current_topic(execution)
        state = self._build_state_from_execution(execution, topic=base_topic)
        state.topic = input_text
        state.start_new_round()
        sequence = 0
        try:
            # Persist and emit the user's message first so ordering is stable.
            user_msg = self._save_user_message(execution_id, input_text, state.round)
            sequence += 1
            yield OrchestrationEvent(
                event_type="user",
                data={
                    "content": input_text,
                    "phase": "user",
                    "round": state.round,
                    "message_id": user_msg["id"],
                    "message_sequence": user_msg["sequence"],
                },
                sequence=sequence,
            )

            filtered_agents = self._filter_agents(agent_instances, target_agent_id)
            recent_context = self._recent_opinions(state, limit=6)
            async for event in self._run_round(
                execution_id,
                filtered_agents,
                state,
                phase="initial",
                recent_opinions=recent_context,
                sequence=sequence,
                override_topic=input_text,
            ):
                sequence = event.sequence
                self._update_execution_state(execution, state)
                yield event
            if target_agent_id is None:
                round_one = list(state.current_round_opinions)
                async for event in self._run_round(
                    execution_id,
                    agent_instances,
                    state,
                    phase="response",
                    recent_opinions=[self._opinion_to_dict(op) for op in round_one],
                    sequence=sequence,
                    override_topic=input_text,
                ):
                    sequence = event.sequence
                    self._update_execution_state(execution, state)
                    yield event

            execution["status"] = "completed"
            execution["current_round"] = state.round
            execution["tokens_used"] = state.tokens_used
            execution["cost"] = state.cost
            execution["shared_state"] = state.to_dict()
            self.store.touch(execution)
            self.store.upsert_execution(execution)

        except Exception as e:
            execution["status"] = "failed"
            execution["error_message"] = str(e)
            self.store.touch(execution)
            self.store.upsert_execution(execution)
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
        self.store.upsert_execution(execution)
        return True

    def delete(self, execution_id: str, user_id: str) -> bool:
        execution = self.get(execution_id, user_id)
        if not execution:
            return False
        self.store.delete_execution(execution_id)
        return True

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
        self.store.upsert_execution_message(msg)

        # Attach stable identifiers so streaming clients can de-dup against persisted messages.
        if isinstance(event.data, dict):
            event.data["message_id"] = msg["id"]
            event.data["message_sequence"] = msg["sequence"]

    def _save_user_message(self, execution_id: str, content: str, round_num: int) -> dict:
        messages = self.store.execution_messages.setdefault(execution_id, [])
        max_seq = max((m.get("sequence", 0) for m in messages), default=0)

        msg = {
            "id": self.store.new_id(),
            "sequence": max_seq + 1,
            "round": round_num,
            "phase": "user",
            "sender_type": "user",
            "sender_id": None,
            "sender_name": "you",
            "content": content,
            "content_type": "text",
            "responding_to": None,
            "target_agent_id": None,
            "confidence": None,
            "wants_to_continue": True,
            "input_tokens": 0,
            "output_tokens": 0,
            "message_metadata": {},
        }
        self.store.touch(msg, created=True)
        self.store.upsert_execution_message(msg)
        return msg

    def _current_topic(self, execution: dict) -> str:
        shared_state = execution.get("shared_state") or {}
        return (shared_state.get("topic") or execution.get("initial_input") or "").strip()

    def _build_state_from_execution(self, execution: dict, *, topic: str) -> OrchestrationState:
        shared_state = execution.get("shared_state") or {}
        state = OrchestrationState(
            topic=topic,
            round=int(shared_state.get("round") or execution.get("current_round", 0)),
            tokens_used=execution.get("tokens_used", 0),
            tokens_budget=execution.get("tokens_budget", 200000),
            cost=execution.get("cost", 0.0),
            cost_budget=execution.get("cost_budget", 10.0),
            summary=shared_state.get("summary", ""),
        )
        if isinstance(shared_state.get("opinions"), list):
            try:
                state.opinions = [
                    Opinion(
                        agent_id=o.get("agent_id"),
                        agent_name=o.get("agent_name"),
                        content=o.get("content") or "",
                        round=int(o.get("round") or 0),
                        phase=o.get("phase") or "unknown",
                        confidence=float(o.get("confidence") or 0.8),
                        wants_to_continue=bool(o.get("wants_to_continue", True)),
                    )
                    for o in shared_state.get("opinions")
                    if isinstance(o, dict) and o.get("agent_id") and o.get("agent_name")
                ]
            except Exception:
                state.opinions = []
        if isinstance(shared_state.get("agent_wants_continue"), dict):
            try:
                state.agent_wants_continue = {str(k): bool(v) for k, v in shared_state["agent_wants_continue"].items()}
            except Exception:
                pass
        return state

    async def _build_agent_instances(self, team: dict, llm_config: Optional[dict]) -> list[AgentInstance]:
        members = [m for m in (team.get("members") or []) if m.get("is_active")]
        members.sort(key=lambda m: m.get("position", 0))
        agent_ids = [m.get("agent_id") for m in members]
        agent_records = [self.store.agents.get(agent_id) for agent_id in agent_ids if self.store.agents.get(agent_id)]
        if not agent_records:
            raise ValueError("No agents in team")

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
        return agent_instances

    def _filter_agents(
        self,
        agent_instances: list[AgentInstance],
        target_agent_id: Optional[str],
    ) -> list[AgentInstance]:
        if not target_agent_id:
            return agent_instances
        return [agent for agent in agent_instances if agent.id == target_agent_id]

    def _recent_opinions(self, state: OrchestrationState, limit: int = 6) -> list[dict]:
        if not state.opinions:
            return []
        return [self._opinion_to_dict(op) for op in state.opinions[-limit:]]

    def _opinion_to_dict(self, opinion: Opinion) -> dict:
        return {
            "agent_id": opinion.agent_id,
            "agent_name": opinion.agent_name,
            "content": opinion.content,
            "round": opinion.round,
            "phase": opinion.phase,
            "confidence": opinion.confidence,
            "wants_to_continue": opinion.wants_to_continue,
        }

    async def _run_round(
        self,
        execution_id: str,
        agent_instances: list[AgentInstance],
        state: OrchestrationState,
        *,
        phase: str,
        recent_opinions: list[dict],
        sequence: int,
        override_topic: Optional[str] = None,
    ) -> AsyncIterator[OrchestrationEvent]:
        state.phase = OrchestrationPhase.PARALLEL if phase == "initial" else OrchestrationPhase.RESPONDING
        state.current_round_opinions.clear()
        topic = override_topic or state.topic
        async def run_agent(agent: AgentInstance):
            response = await agent.generate_opinion(
                topic=topic,
                discussion_summary=state.summary,
                recent_opinions=recent_opinions,
                phase="initial" if phase == "initial" else "response",
            )
            return agent, response

        pending = {asyncio.create_task(run_agent(agent)) for agent in agent_instances}

        while pending:
            done, _ = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                pending.discard(task)
                try:
                    agent, response = task.result()
                except Exception as e:
                    sequence += 1
                    yield OrchestrationEvent(
                        event_type="status",
                        data={"message": f"{agent.name} 回复失败: {e}", "phase": "agent_error"},
                        agent_id=agent.id,
                        sequence=sequence,
                    )
                    continue

                opinion = Opinion(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    content=response.content,
                    round=state.round,
                    phase=phase,
                    confidence=response.confidence,
                    wants_to_continue=response.wants_to_continue,
                    responding_to=response.responding_to,
                    input_tokens=response.metadata.get("input_tokens", 0),
                    output_tokens=response.metadata.get("output_tokens", 0),
                )
                state.add_opinion(opinion)

                data = {
                    "content": response.content,
                    "agent_name": agent.name,
                    "phase": phase,
                    "round": state.round,
                    "confidence": response.confidence,
                    "wants_to_continue": response.wants_to_continue,
                    "responding_to": response.responding_to,
                    "input_tokens": response.metadata.get("input_tokens", 0),
                    "output_tokens": response.metadata.get("output_tokens", 0),
                    "metadata": response.metadata,
                }
                sequence += 1
                event = OrchestrationEvent(event_type="opinion", data=data, agent_id=agent.id, sequence=sequence)
                self._save_message(execution_id, event, state.round)
                yield event

    def _update_execution_state(self, execution: dict, state: OrchestrationState) -> None:
        execution["current_round"] = state.round
        execution["tokens_used"] = state.tokens_used
        execution["cost"] = state.cost
        execution["shared_state"] = state.to_dict()
        self.store.touch(execution)
        self.store.upsert_execution(execution)
