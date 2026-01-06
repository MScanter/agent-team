"""
Pipeline orchestrator for sequential processing.
"""

from typing import AsyncIterator, Optional

from app.agents.base import AgentInstance
from app.orchestration.base import (
    Orchestrator,
    OrchestrationState,
    OrchestrationEvent,
    OrchestrationPhase,
    Opinion,
)


class PipelineOrchestrator(Orchestrator):
    """
    Pipeline orchestrator for sequential processing.

    Flow:
    Input → Agent A → Agent B → Agent C → Output

    Each agent processes the output of the previous agent.
    """

    def __init__(self, config: dict = None):
        super().__init__(config)
        self._sequence = 0

    @property
    def mode_name(self) -> str:
        return "pipeline"

    def _next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    async def run(
        self,
        agents: list[AgentInstance],
        state: OrchestrationState,
    ) -> AsyncIterator[OrchestrationEvent]:
        """Run pipeline processing."""

        state.phase = OrchestrationPhase.INITIALIZING
        state.agent_ids = [a.id for a in agents]
        state.active_agent_ids = state.agent_ids.copy()

        yield OrchestrationEvent(
            event_type="status",
            data={"message": "Pipeline started", "stages": len(agents)},
            sequence=self._next_sequence(),
        )

        # Sort agents by position if available in config
        sorted_agents = self._sort_agents_by_position(agents)

        current_input = state.topic
        state.round = 1

        for i, agent in enumerate(sorted_agents):
            stage_name = f"Stage {i + 1}: {agent.name}"

            state.phase = OrchestrationPhase.SEQUENTIAL
            yield OrchestrationEvent(
                event_type="status",
                data={"message": f"Processing {stage_name}", "stage": i + 1},
                sequence=self._next_sequence(),
            )

            try:
                # Each agent processes the current input
                response = await agent.generate_opinion(
                    topic=current_input,
                    discussion_summary="",
                    recent_opinions=[],
                    phase="initial",
                )

                opinion = Opinion(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    content=response.content,
                    round=state.round,
                    phase=f"stage_{i + 1}",
                    confidence=response.confidence,
                    wants_to_continue=True,
                    input_tokens=response.metadata.get("input_tokens", 0),
                    output_tokens=response.metadata.get("output_tokens", 0),
                )
                state.add_opinion(opinion)

                yield OrchestrationEvent(
                    event_type="opinion",
                    data={
                        "agent_name": agent.name,
                        "content": response.content,
                        "stage": i + 1,
                        "stage_name": stage_name,
                    },
                    agent_id=agent.id,
                    sequence=self._next_sequence(),
                )

                # Update input for next stage
                current_input = self._prepare_next_input(state.topic, response.content, i + 1)

                # Check budget
                if not self.should_continue(state):
                    yield OrchestrationEvent(
                        event_type="status",
                        data={"message": "Budget exceeded, stopping pipeline"},
                        sequence=self._next_sequence(),
                    )
                    break

            except Exception as e:
                yield OrchestrationEvent(
                    event_type="error",
                    data={"message": f"Stage {i + 1} failed: {str(e)}", "stage": i + 1},
                    agent_id=agent.id,
                    sequence=self._next_sequence(),
                )

                # Decide whether to continue or abort based on config
                if self.config.get("abort_on_error", True):
                    state.should_terminate = True
                    state.termination_reason = f"Pipeline failed at stage {i + 1}"
                    state.error = str(e)
                    break

        # Complete
        state.phase = OrchestrationPhase.COMPLETED

        # Generate final output from last stage
        final_output = state.opinions[-1].content if state.opinions else ""

        yield OrchestrationEvent(
            event_type="done",
            data={
                "final_output": final_output,
                "stages_completed": len(state.opinions),
                "tokens_used": state.tokens_used,
            },
            sequence=self._next_sequence(),
        )

    def _sort_agents_by_position(self, agents: list[AgentInstance]) -> list[AgentInstance]:
        """Sort agents by their configured position."""
        positions = self.config.get("positions", {})
        return sorted(
            agents,
            key=lambda a: positions.get(a.id, 999),
        )

    def _prepare_next_input(self, original_topic: str, previous_output: str, stage: int) -> str:
        """Prepare input for the next stage."""
        return f"""原始任务：{original_topic}

上一阶段（第{stage}阶段）的输出：
{previous_output}

请基于上述内容，从你的专业角度进行处理和完善。"""

    async def handle_followup(
        self,
        followup: str,
        agents: list[AgentInstance],
        state: OrchestrationState,
        target_agent_id: Optional[str] = None,
    ) -> AsyncIterator[OrchestrationEvent]:
        """Handle follow-up by re-running pipeline with new input."""

        yield OrchestrationEvent(
            event_type="status",
            data={"message": "Re-running pipeline with follow-up"},
            sequence=self._next_sequence(),
        )

        # Update topic and re-run
        combined_input = f"""原始任务：{state.topic}

之前的处理结果：
{state.opinions[-1].content if state.opinions else "无"}

追问/新要求：{followup}"""

        state.topic = combined_input
        state.opinions.clear()

        async for event in self.run(agents, state):
            yield event
