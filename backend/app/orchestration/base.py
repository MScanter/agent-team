"""
Base orchestrator class and common types.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Optional

from app.agents.base import AgentInstance, AgentResponse


class OrchestrationPhase(str, Enum):
    """Phases of orchestration."""

    INITIALIZING = "initializing"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    RESPONDING = "responding"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    PAUSED = "paused"
    FAILED = "failed"


@dataclass
class Opinion:
    """An opinion from an agent."""

    agent_id: str
    agent_name: str
    content: str
    round: int
    phase: str
    confidence: float = 0.8
    wants_to_continue: bool = True
    responding_to: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class OrchestrationState:
    """
    Shared state for orchestration.

    This is the central state object passed between agents and the orchestrator.
    """

    # Topic
    topic: str
    round: int = 0
    phase: OrchestrationPhase = OrchestrationPhase.INITIALIZING

    # Participants
    agent_ids: list[str] = field(default_factory=list)
    active_agent_ids: list[str] = field(default_factory=list)

    # Opinions
    opinions: list[Opinion] = field(default_factory=list)
    current_round_opinions: list[Opinion] = field(default_factory=list)

    # Summary
    summary: str = ""
    key_points: list[str] = field(default_factory=list)
    consensus: list[str] = field(default_factory=list)
    disagreements: list[dict] = field(default_factory=list)

    # Agent states
    agent_wants_continue: dict[str, bool] = field(default_factory=dict)

    # Budget
    tokens_used: int = 0
    tokens_budget: int = 200000
    cost: float = 0.0
    cost_budget: float = 10.0

    # Control
    should_terminate: bool = False
    termination_reason: Optional[str] = None
    error: Optional[str] = None

    def add_opinion(self, opinion: Opinion):
        """Add an opinion and update token usage."""
        self.opinions.append(opinion)
        self.current_round_opinions.append(opinion)
        self.tokens_used += opinion.input_tokens + opinion.output_tokens
        self.agent_wants_continue[opinion.agent_id] = opinion.wants_to_continue

    def start_new_round(self):
        """Start a new discussion round."""
        self.round += 1
        self.current_round_opinions.clear()

    def check_budget(self) -> tuple[bool, Optional[str]]:
        """Check if budget is exceeded."""
        token_ratio = self.tokens_used / self.tokens_budget
        if token_ratio >= 1.0:
            return True, "Token budget exceeded"
        if self.cost >= self.cost_budget:
            return True, "Cost budget exceeded"
        return False, None

    def check_termination(self) -> tuple[bool, Optional[str]]:
        """Check if discussion should terminate."""
        # Already marked for termination
        if self.should_terminate:
            return True, self.termination_reason

        # Budget check
        exceeded, reason = self.check_budget()
        if exceeded:
            return True, reason

        # All agents want to stop
        if self.agent_wants_continue and all(
            not wants for wants in self.agent_wants_continue.values()
        ):
            return True, "All agents have finished"

        return False, None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "topic": self.topic,
            "round": self.round,
            "phase": self.phase.value,
            "agent_ids": self.agent_ids,
            "active_agent_ids": self.active_agent_ids,
            "opinions": [
                {
                    "agent_id": op.agent_id,
                    "agent_name": op.agent_name,
                    "content": op.content,
                    "round": op.round,
                    "phase": op.phase,
                    "confidence": op.confidence,
                    "wants_to_continue": op.wants_to_continue,
                }
                for op in self.opinions
            ],
            "summary": self.summary,
            "key_points": self.key_points,
            "consensus": self.consensus,
            "disagreements": self.disagreements,
            "tokens_used": self.tokens_used,
            "tokens_budget": self.tokens_budget,
            "cost": self.cost,
            "cost_budget": self.cost_budget,
            "should_terminate": self.should_terminate,
            "termination_reason": self.termination_reason,
        }


@dataclass
class OrchestrationEvent:
    """Event emitted during orchestration."""

    event_type: str  # opinion, status, summary, error, done
    data: Any
    agent_id: Optional[str] = None
    sequence: int = 0


class Orchestrator(ABC):
    """
    Abstract base class for orchestrators.

    Orchestrators manage the flow of discussion between agents.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}

    @property
    @abstractmethod
    def mode_name(self) -> str:
        """Name of this orchestration mode."""
        pass

    @abstractmethod
    async def run(
        self,
        agents: list[AgentInstance],
        state: OrchestrationState,
    ) -> AsyncIterator[OrchestrationEvent]:
        """
        Run the orchestration.

        Args:
            agents: List of agent instances to orchestrate
            state: Shared orchestration state

        Yields:
            OrchestrationEvent for each step
        """
        pass

    @abstractmethod
    async def handle_followup(
        self,
        followup: str,
        agents: list[AgentInstance],
        state: OrchestrationState,
        target_agent_id: Optional[str] = None,
    ) -> AsyncIterator[OrchestrationEvent]:
        """
        Handle a follow-up question.

        Args:
            followup: The follow-up question
            agents: List of agent instances
            state: Current orchestration state
            target_agent_id: Specific agent to address (optional)

        Yields:
            OrchestrationEvent for each step
        """
        pass

    def should_continue(self, state: OrchestrationState) -> bool:
        """Check if orchestration should continue."""
        should_terminate, _ = state.check_termination()
        return not should_terminate

    async def generate_summary(
        self,
        state: OrchestrationState,
    ) -> str:
        """Generate summary of the discussion. Override in subclasses."""
        return state.summary
