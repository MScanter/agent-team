"""
Roundtable orchestrator for open discussion.
"""

import asyncio
from typing import AsyncIterator, Optional

from app.agents.base import AgentInstance
from app.agents.coordinator import Coordinator
from app.llm import LLMProvider
from app.orchestration.base import (
    Orchestrator,
    OrchestrationState,
    OrchestrationEvent,
    OrchestrationPhase,
    Opinion,
)


class RoundtableOrchestrator(Orchestrator):
    """
    Roundtable discussion orchestrator.

    Flow:
    1. Phase 1 (Parallel): All agents give initial opinions simultaneously
    2. Phase 2 (Sequential): Agents respond to each other's opinions
    3. Repeat until termination condition is met
    """

    def __init__(self, config: dict = None, *, coordinator_llm: Optional[LLMProvider] = None):
        super().__init__(config)
        self.coordinator = Coordinator(coordinator_llm)
        self._sequence = 0
        self._interactive = bool(self.config.get("interactive", True))
        self._enable_response_phase = bool(
            self.config.get("enable_response_phase", False if self._interactive else True)
        )
        self._max_rounds = int(self.config.get("max_rounds", 0))

    @property
    def mode_name(self) -> str:
        return "roundtable"

    def _next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    async def run(
        self,
        agents: list[AgentInstance],
        state: OrchestrationState,
    ) -> AsyncIterator[OrchestrationEvent]:
        """Run roundtable discussion."""

        # Initialize
        state.phase = OrchestrationPhase.INITIALIZING
        state.agent_ids = [a.id for a in agents]
        state.active_agent_ids = state.agent_ids.copy()

        yield OrchestrationEvent(
            event_type="status",
            data={"message": "讨论已开始", "phase": "initializing"},
            sequence=self._next_sequence(),
        )

        # Drop agents that opted out in previous rounds.
        state.active_agent_ids = [
            agent_id for agent_id in state.active_agent_ids if state.agent_wants_continue.get(agent_id, True)
        ]
        if not state.active_agent_ids:
            state.should_terminate = True
            state.termination_reason = "No active agents remaining"

        if self._max_rounds and state.round >= self._max_rounds:
            state.should_terminate = True
            state.termination_reason = "Reached max rounds"

        if not self.should_continue(state):
            async for event in self._finalize(state):
                yield event
            return

        async for event in self._run_one_round(agents, state):
            yield event
        yield OrchestrationEvent(
            event_type="summary",
            data={
                "round": state.round,
                "summary": state.summary,
                "key_points": state.key_points,
            },
            sequence=self._next_sequence(),
        )

        # Interactive mode pauses after each round and waits for user follow-up.
        if self._interactive:
            yield OrchestrationEvent(
                event_type="await_input",
                data={"message": "等待你的下一条输入（继续讨论/补充信息/提出疑问）", "phase": "awaiting_user_input", "round": state.round},
                sequence=self._next_sequence(),
            )
            return

        # Batch mode: keep running until termination.
        while self.should_continue(state):
            # Drop agents that opted out in previous rounds.
            state.active_agent_ids = [
                agent_id for agent_id in state.active_agent_ids if state.agent_wants_continue.get(agent_id, True)
            ]
            if not state.active_agent_ids:
                state.should_terminate = True
                state.termination_reason = "No active agents remaining"
                break
            if self._max_rounds and state.round >= self._max_rounds:
                state.should_terminate = True
                state.termination_reason = "Reached max rounds"
                break

            async for event in self._run_one_round(agents, state):
                yield event
            yield OrchestrationEvent(
                event_type="summary",
                data={
                    "round": state.round,
                    "summary": state.summary,
                    "key_points": state.key_points,
                },
                sequence=self._next_sequence(),
            )

        async for event in self._finalize(state):
            yield event

    async def _run_one_round(
        self,
        agents: list[AgentInstance],
        state: OrchestrationState,
    ) -> AsyncIterator[OrchestrationEvent]:
        state.start_new_round()

        state.phase = OrchestrationPhase.PARALLEL
        yield OrchestrationEvent(
            event_type="status",
            data={"message": f"第 {state.round} 轮：并行发言", "round": state.round, "phase": "parallel"},
            sequence=self._next_sequence(),
        )

        # Parallel opinions
        async for event in self._parallel_phase(agents, state):
            yield event

        # Sequential responses (optional). In interactive mode this is off by default, because it
        # often duplicates content and hurts user-directed chat quality.
        if self._enable_response_phase:
            state.phase = OrchestrationPhase.SEQUENTIAL
            yield OrchestrationEvent(
                event_type="status",
                data={"message": f"第 {state.round} 轮：互相回应", "round": state.round, "phase": "response"},
                sequence=self._next_sequence(),
            )
            async for event in self._sequential_phase(agents, state):
                yield event

        # Update summary
        state.phase = OrchestrationPhase.SUMMARIZING
        summary = await self.coordinator.generate_summary(
            topic=state.topic,
            opinions=[{"agent_name": op.agent_name, "content": op.content} for op in state.current_round_opinions],
            previous_summary=state.summary,
        )
        state.summary = summary.summary_text
        state.key_points = summary.key_points
        state.consensus = summary.consensus
        state.disagreements = summary.disagreements

    async def _finalize(self, state: OrchestrationState) -> AsyncIterator[OrchestrationEvent]:
        state.phase = OrchestrationPhase.COMPLETED
        final_summary = await self.coordinator.generate_final_summary(
            topic=state.topic,
            all_opinions=[{"agent_name": op.agent_name, "content": op.content, "round": op.round} for op in state.opinions],
            summary=self.coordinator._summary,
        )
        yield OrchestrationEvent(
            event_type="done",
            data={"final_summary": final_summary, "total_rounds": state.round, "tokens_used": state.tokens_used},
            sequence=self._next_sequence(),
        )

    async def _parallel_phase(
        self,
        agents: list[AgentInstance],
        state: OrchestrationState,
    ) -> AsyncIterator[OrchestrationEvent]:
        """Execute parallel phase where all agents speak simultaneously."""

        # Prepare recent opinions for context
        recent_opinions = [
            {"agent_name": op.agent_name, "content": op.content}
            for op in state.opinions[-10:]  # Last 10 opinions
        ]

        # Create tasks for all agents
        async def get_opinion(agent: AgentInstance) -> tuple[AgentInstance, Optional[Exception]]:
            try:
                response = await agent.generate_opinion(
                    topic=state.topic,
                    discussion_summary=state.summary,
                    recent_opinions=recent_opinions,
                    phase="initial",
                )
                return agent, response, None
            except Exception as e:
                return agent, None, e

        # Run all agents in parallel
        tasks = [get_opinion(agent) for agent in agents if agent.id in state.active_agent_ids]
        results = await asyncio.gather(*tasks)

        for agent, response, error in results:
            if error:
                yield OrchestrationEvent(
                    event_type="error",
                    data={"message": f"Agent {agent.name} failed: {str(error)}"},
                    agent_id=agent.id,
                    sequence=self._next_sequence(),
                )
                continue

            opinion = Opinion(
                agent_id=agent.id,
                agent_name=agent.name,
                content=response.content,
                round=state.round,
                phase="parallel",
                confidence=response.confidence,
                wants_to_continue=response.wants_to_continue,
                input_tokens=response.metadata.get("input_tokens", 0),
                output_tokens=response.metadata.get("output_tokens", 0),
            )
            state.add_opinion(opinion)

            yield OrchestrationEvent(
                event_type="opinion",
                data={
                    "agent_name": agent.name,
                    "content": response.content,
                    "confidence": response.confidence,
                    "wants_to_continue": response.wants_to_continue,
                    "round": state.round,
                    "phase": "parallel",
                },
                agent_id=agent.id,
                sequence=self._next_sequence(),
            )

    async def _sequential_phase(
        self,
        agents: list[AgentInstance],
        state: OrchestrationState,
    ) -> AsyncIterator[OrchestrationEvent]:
        """Execute sequential phase where agents respond to each other."""

        # Get opinions from parallel phase
        parallel_opinions = [
            {"agent_name": op.agent_name, "content": op.content, "agent_id": op.agent_id}
            for op in state.current_round_opinions
        ]

        # Each agent responds in sequence
        for agent in agents:
            if agent.id not in state.active_agent_ids:
                continue

            # Skip if agent doesn't want to continue
            if not state.agent_wants_continue.get(agent.id, True):
                continue

            # Filter out agent's own opinion
            other_opinions = [
                op for op in parallel_opinions if op["agent_id"] != agent.id
            ]

            try:
                response = await agent.generate_opinion(
                    topic=state.topic,
                    discussion_summary=state.summary,
                    recent_opinions=other_opinions,
                    phase="response",
                )

                opinion = Opinion(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    content=response.content,
                    round=state.round,
                    phase="response",
                    confidence=response.confidence,
                    wants_to_continue=response.wants_to_continue,
                    responding_to=response.responding_to,
                    input_tokens=response.metadata.get("input_tokens", 0),
                    output_tokens=response.metadata.get("output_tokens", 0),
                )
                state.add_opinion(opinion)

                yield OrchestrationEvent(
                    event_type="opinion",
                    data={
                        "agent_name": agent.name,
                        "content": response.content,
                        "confidence": response.confidence,
                        "wants_to_continue": response.wants_to_continue,
                        "phase": "response",
                        "round": state.round,
                    },
                    agent_id=agent.id,
                    sequence=self._next_sequence(),
                )

            except Exception as e:
                yield OrchestrationEvent(
                    event_type="error",
                    data={"message": f"Agent {agent.name} failed: {str(e)}"},
                    agent_id=agent.id,
                    sequence=self._next_sequence(),
                )

    async def handle_followup(
        self,
        followup: str,
        agents: list[AgentInstance],
        state: OrchestrationState,
        target_agent_id: Optional[str] = None,
    ) -> AsyncIterator[OrchestrationEvent]:
        """Handle follow-up question."""

        yield OrchestrationEvent(
            event_type="status",
            data={"message": "正在处理你的输入"},
            sequence=self._next_sequence(),
        )

        # Merge follow-up into topic so the next round has full context.
        state.topic = f"{state.topic}\n\n用户输入：{followup}"

        # Route the follow-up
        if target_agent_id:
            # Direct to specific agent
            target_agents = [a for a in agents if a.id == target_agent_id]
        else:
            # Let coordinator decide
            routing = await self.coordinator.route_followup(
                followup=followup,
                available_agents=[
                    {"id": a.id, "name": a.name, "domain": a.config.domain}
                    for a in agents
                ],
                current_summary=self.coordinator._summary,
            )

            if routing["type"] == "summary":
                # Just generate summary
                summary = await self.coordinator.generate_final_summary(
                    topic=state.topic,
                    all_opinions=[
                        {"agent_name": op.agent_name, "content": op.content, "round": op.round}
                        for op in state.opinions
                    ],
                    summary=self.coordinator._summary,
                )
                yield OrchestrationEvent(
                    event_type="summary",
                    data={"summary": summary, "phase": "followup"},
                    sequence=self._next_sequence(),
                )
                if self._interactive:
                    yield OrchestrationEvent(
                        event_type="await_input",
                        data={"message": "等待你的下一条输入（继续讨论/补充信息/提出疑问）", "phase": "awaiting_user_input"},
                        sequence=self._next_sequence(),
                    )
                return

            target_agents = [a for a in agents if a.id in routing.get("agent_ids", [])]

        # Interactive follow-up: run one more discussion round.
        state.active_agent_ids = [a.id for a in target_agents] if target_agents else state.active_agent_ids
        async for event in self._run_one_round(agents, state):
            yield event
        yield OrchestrationEvent(
            event_type="summary",
            data={"round": state.round, "summary": state.summary, "key_points": state.key_points},
            sequence=self._next_sequence(),
        )
        if self._interactive:
            yield OrchestrationEvent(
                event_type="await_input",
                data={"message": "等待你的下一条输入（继续讨论/补充信息/提出疑问）", "phase": "awaiting_user_input", "round": state.round},
                sequence=self._next_sequence(),
            )
