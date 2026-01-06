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
            data={"message": "Discussion started", "phase": "initializing"},
            sequence=self._next_sequence(),
        )

        while self.should_continue(state):
            state.start_new_round()

            # Phase 1: Parallel opinions
            state.phase = OrchestrationPhase.PARALLEL
            yield OrchestrationEvent(
                event_type="status",
                data={"message": f"Round {state.round} - Parallel phase", "round": state.round},
                sequence=self._next_sequence(),
            )

            async for event in self._parallel_phase(agents, state):
                yield event

            # Check termination after parallel phase
            if not self.should_continue(state):
                break

            # Phase 2: Sequential responses
            state.phase = OrchestrationPhase.SEQUENTIAL
            yield OrchestrationEvent(
                event_type="status",
                data={"message": f"Round {state.round} - Response phase", "round": state.round},
                sequence=self._next_sequence(),
            )

            async for event in self._sequential_phase(agents, state):
                yield event

            # Update summary
            state.phase = OrchestrationPhase.SUMMARIZING
            summary = await self.coordinator.generate_summary(
                topic=state.topic,
                opinions=[
                    {"agent_name": op.agent_name, "content": op.content}
                    for op in state.current_round_opinions
                ],
                previous_summary=state.summary,
            )
            state.summary = summary.summary_text
            state.key_points = summary.key_points
            state.consensus = summary.consensus
            state.disagreements = summary.disagreements

            yield OrchestrationEvent(
                event_type="summary",
                data={
                    "round": state.round,
                    "summary": state.summary,
                    "key_points": state.key_points,
                },
                sequence=self._next_sequence(),
            )

        # Final summary
        state.phase = OrchestrationPhase.COMPLETED
        final_summary = await self.coordinator.generate_final_summary(
            topic=state.topic,
            all_opinions=[
                {
                    "agent_name": op.agent_name,
                    "content": op.content,
                    "round": op.round,
                }
                for op in state.opinions
            ],
            summary=self.coordinator._summary,
        )

        yield OrchestrationEvent(
            event_type="done",
            data={
                "final_summary": final_summary,
                "total_rounds": state.round,
                "tokens_used": state.tokens_used,
            },
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
            data={"message": "Processing follow-up"},
            sequence=self._next_sequence(),
        )

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
                    data={"summary": summary},
                    sequence=self._next_sequence(),
                )
                return

            target_agents = [a for a in agents if a.id in routing.get("agent_ids", [])]

        # Get responses from target agents
        state.start_new_round()
        for agent in target_agents:
            try:
                response = await agent.generate_opinion(
                    topic=followup,
                    discussion_summary=state.summary,
                    recent_opinions=[],
                    phase="initial",
                )

                opinion = Opinion(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    content=response.content,
                    round=state.round,
                    phase="followup",
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
                        "phase": "followup",
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
