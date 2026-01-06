"""
Debate orchestrator for adversarial discussion.
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


class DebateOrchestrator(Orchestrator):
    """
    Debate orchestrator for adversarial discussion.

    Flow:
    1. Pro team presents opening argument
    2. Con team presents opening argument
    3. Alternating rebuttals
    4. Judge summarizes and decides
    """

    def __init__(self, config: dict = None):
        super().__init__(config)
        self._sequence = 0
        self._pro_team: list[str] = config.get("pro_team", []) if config else []
        self._con_team: list[str] = config.get("con_team", []) if config else []
        self._judge_id: Optional[str] = config.get("judge_id") if config else None
        self._max_rounds: int = config.get("max_rounds", 3) if config else 3

    @property
    def mode_name(self) -> str:
        return "debate"

    def _next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    async def run(
        self,
        agents: list[AgentInstance],
        state: OrchestrationState,
    ) -> AsyncIterator[OrchestrationEvent]:
        """Run debate."""

        state.phase = OrchestrationPhase.INITIALIZING
        state.agent_ids = [a.id for a in agents]
        state.active_agent_ids = state.agent_ids.copy()

        # Categorize agents
        pro_agents = [a for a in agents if a.id in self._pro_team]
        con_agents = [a for a in agents if a.id in self._con_team]
        judge = next((a for a in agents if a.id == self._judge_id), None)

        # Auto-assign if not configured
        if not pro_agents and not con_agents:
            mid = len(agents) // 2
            pro_agents = agents[:mid]
            con_agents = agents[mid:] if not judge else agents[mid:-1]
            if not judge and agents:
                judge = agents[-1]

        yield OrchestrationEvent(
            event_type="status",
            data={
                "message": "Debate started",
                "pro_team": [a.name for a in pro_agents],
                "con_team": [a.name for a in con_agents],
                "judge": judge.name if judge else "None",
            },
            sequence=self._next_sequence(),
        )

        # Opening arguments
        yield OrchestrationEvent(
            event_type="status",
            data={"message": "Opening arguments phase"},
            sequence=self._next_sequence(),
        )

        # Pro opening
        state.round = 1
        async for event in self._team_argument(
            pro_agents, state, "opening", "正方", []
        ):
            yield event

        # Con opening
        pro_opinions = [
            {"agent_name": op.agent_name, "content": op.content}
            for op in state.current_round_opinions
        ]
        async for event in self._team_argument(
            con_agents, state, "opening", "反方", pro_opinions
        ):
            yield event

        # Rebuttals
        for round_num in range(1, self._max_rounds + 1):
            state.start_new_round()

            if not self.should_continue(state):
                break

            yield OrchestrationEvent(
                event_type="status",
                data={"message": f"Rebuttal round {round_num}"},
                sequence=self._next_sequence(),
            )

            # Get last round opinions
            last_opinions = [
                {"agent_name": op.agent_name, "content": op.content, "team": "正方" if op.agent_id in [a.id for a in pro_agents] else "反方"}
                for op in state.opinions[-len(pro_agents) - len(con_agents):]
            ]

            # Pro rebuttal
            con_opinions = [op for op in last_opinions if op["team"] == "反方"]
            async for event in self._team_argument(
                pro_agents, state, "rebuttal", "正方", con_opinions
            ):
                yield event

            # Con rebuttal
            pro_opinions = [op for op in last_opinions if op["team"] == "正方"]
            async for event in self._team_argument(
                con_agents, state, "rebuttal", "反方", pro_opinions
            ):
                yield event

        # Judge's verdict
        if judge:
            state.phase = OrchestrationPhase.SUMMARIZING
            yield OrchestrationEvent(
                event_type="status",
                data={"message": "Judge's verdict"},
                sequence=self._next_sequence(),
            )

            async for event in self._judge_verdict(judge, state, pro_agents, con_agents):
                yield event

        state.phase = OrchestrationPhase.COMPLETED
        yield OrchestrationEvent(
            event_type="done",
            data={
                "total_rounds": state.round,
                "tokens_used": state.tokens_used,
            },
            sequence=self._next_sequence(),
        )

    async def _team_argument(
        self,
        team_agents: list[AgentInstance],
        state: OrchestrationState,
        phase: str,
        team_name: str,
        opponent_opinions: list[dict],
    ) -> AsyncIterator[OrchestrationEvent]:
        """Get argument from a team."""

        for agent in team_agents:
            prompt_addon = ""
            if phase == "opening":
                prompt_addon = f"\n\n你是{team_name}。请就上述论题发表你的开场论点。"
            else:
                opponent_text = "\n".join(
                    f"- {op['agent_name']}: {op['content']}"
                    for op in opponent_opinions
                )
                prompt_addon = f"\n\n你是{team_name}。对方的观点：\n{opponent_text}\n\n请进行反驳。"

            try:
                response = await agent.generate_opinion(
                    topic=state.topic + prompt_addon,
                    discussion_summary=state.summary,
                    recent_opinions=opponent_opinions,
                    phase=phase,
                )

                opinion = Opinion(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    content=response.content,
                    round=state.round,
                    phase=f"{team_name}_{phase}",
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
                        "team": team_name,
                        "phase": phase,
                    },
                    agent_id=agent.id,
                    sequence=self._next_sequence(),
                )

            except Exception as e:
                yield OrchestrationEvent(
                    event_type="error",
                    data={"message": f"{team_name} {agent.name} failed: {str(e)}"},
                    agent_id=agent.id,
                    sequence=self._next_sequence(),
                )

    async def _judge_verdict(
        self,
        judge: AgentInstance,
        state: OrchestrationState,
        pro_agents: list[AgentInstance],
        con_agents: list[AgentInstance],
    ) -> AsyncIterator[OrchestrationEvent]:
        """Get judge's verdict."""

        # Compile all arguments
        pro_arguments = [
            f"- {op.agent_name}: {op.content}"
            for op in state.opinions
            if op.agent_id in [a.id for a in pro_agents]
        ]
        con_arguments = [
            f"- {op.agent_name}: {op.content}"
            for op in state.opinions
            if op.agent_id in [a.id for a in con_agents]
        ]

        verdict_prompt = f"""作为裁判，请评判以下辩论：

论题：{state.topic}

正方观点：
{chr(10).join(pro_arguments)}

反方观点：
{chr(10).join(con_arguments)}

请给出你的裁决，包括：
1. 双方的主要论点总结
2. 各方的优势和不足
3. 你的最终判断
"""

        try:
            response = await judge.generate_opinion(
                topic=verdict_prompt,
                discussion_summary="",
                recent_opinions=[],
                phase="verdict",
            )

            opinion = Opinion(
                agent_id=judge.id,
                agent_name=judge.name,
                content=response.content,
                round=state.round,
                phase="verdict",
                confidence=response.confidence,
                wants_to_continue=False,
                input_tokens=response.metadata.get("input_tokens", 0),
                output_tokens=response.metadata.get("output_tokens", 0),
            )
            state.add_opinion(opinion)

            # Update summary with verdict
            state.summary = response.content

            yield OrchestrationEvent(
                event_type="opinion",
                data={
                    "agent_name": judge.name,
                    "content": response.content,
                    "role": "judge",
                    "phase": "verdict",
                },
                agent_id=judge.id,
                sequence=self._next_sequence(),
            )

        except Exception as e:
            yield OrchestrationEvent(
                event_type="error",
                data={"message": f"Judge failed: {str(e)}"},
                agent_id=judge.id,
                sequence=self._next_sequence(),
            )

    async def handle_followup(
        self,
        followup: str,
        agents: list[AgentInstance],
        state: OrchestrationState,
        target_agent_id: Optional[str] = None,
    ) -> AsyncIterator[OrchestrationEvent]:
        """Handle follow-up by continuing debate."""

        yield OrchestrationEvent(
            event_type="status",
            data={"message": "Adding follow-up to debate"},
            sequence=self._next_sequence(),
        )

        # Add follow-up as new topic and continue
        state.topic = f"{state.topic}\n\n追加问题：{followup}"

        # Run one more round
        pro_agents = [a for a in agents if a.id in self._pro_team]
        con_agents = [a for a in agents if a.id in self._con_team]

        state.start_new_round()

        async for event in self._team_argument(pro_agents, state, "followup", "正方", []):
            yield event

        async for event in self._team_argument(con_agents, state, "followup", "反方", []):
            yield event
