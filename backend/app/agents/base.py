"""
Base agent class and configuration.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from app.llm import LLMProvider, Message, MessageRole, LLMResponse


@dataclass
class AgentConfig:
    """Configuration for an agent instance."""

    id: str
    name: str
    system_prompt: str

    # LLM settings
    model_id: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048

    # Team role
    domain: Optional[str] = None
    collaboration_style: str = "supportive"
    speaking_priority: int = 5

    # Interaction rules
    can_challenge: bool = True
    can_be_challenged: bool = True
    defer_to: list[str] = field(default_factory=list)

    # Capabilities
    tools: list[str] = field(default_factory=list)
    memory_enabled: bool = False

    # Metadata
    avatar: Optional[str] = None
    description: Optional[str] = None


@dataclass
class AgentResponse:
    """Response from an agent."""

    content: str
    confidence: float = 0.8
    wants_to_continue: bool = True
    responding_to: Optional[str] = None  # Agent ID being responded to
    metadata: dict = field(default_factory=dict)


class AgentInstance:
    """
    Runtime instance of an agent.

    Handles LLM interactions and maintains agent-specific context.
    """

    def __init__(
        self,
        config: AgentConfig,
        llm_provider: LLMProvider,
    ):
        self.config = config
        self.llm = llm_provider
        self._conversation_history: list[Message] = []
        self._opinions: list[str] = []

    @property
    def id(self) -> str:
        return self.config.id

    @property
    def name(self) -> str:
        return self.config.name

    def _build_system_message(self) -> Message:
        """Build the system message for this agent."""
        return Message(
            role=MessageRole.SYSTEM,
            content=self.config.system_prompt,
        )

    def _build_context_message(
        self,
        discussion_summary: str,
        recent_opinions: list[dict],
        current_topic: str,
    ) -> str:
        """Build context message with discussion state."""
        context_parts = [f"## 当前讨论主题\n{current_topic}"]

        if discussion_summary:
            context_parts.append(f"## 讨论摘要\n{discussion_summary}")

        if recent_opinions:
            opinions_text = "\n".join(
                f"- **{op['agent_name']}**: {op['content']}"
                for op in recent_opinions
            )
            context_parts.append(f"## 其他专家的观点\n{opinions_text}")

        if self._opinions:
            my_opinions = "\n".join(f"- {op}" for op in self._opinions[-3:])
            context_parts.append(f"## 你之前的观点\n{my_opinions}")

        return "\n\n".join(context_parts)

    async def generate_opinion(
        self,
        topic: str,
        discussion_summary: str = "",
        recent_opinions: list[dict] = None,
        phase: str = "initial",
    ) -> AgentResponse:
        """
        Generate an opinion on the current topic.

        Args:
            topic: The discussion topic or question
            discussion_summary: Summary of discussion so far
            recent_opinions: Recent opinions from other agents
            phase: Discussion phase ('initial' or 'response')

        Returns:
            AgentResponse with the agent's opinion
        """
        recent_opinions = recent_opinions or []

        # Build messages
        messages = [self._build_system_message()]

        # Add context
        context = self._build_context_message(
            discussion_summary,
            recent_opinions,
            topic,
        )
        messages.append(Message(role=MessageRole.USER, content=context))

        # Add phase-specific instruction
        if phase == "initial":
            instruction = (
                "请就上述主题发表你的专业观点。\n\n"
                "要求：\n"
                "1. 从你的专业角度分析\n"
                "2. 给出具体、有见地的观点\n"
                "3. 如果有其他专家的观点，可以参考但要保持独立思考\n\n"
                "请直接输出你的观点，不要加前缀。"
            )
        else:
            instruction = (
                "请根据其他专家的观点进行回应。\n\n"
                "你可以：\n"
                "1. 补充自己的观点\n"
                "2. 对某位专家的观点提出质疑或不同看法\n"
                "3. 表示同意某个观点并说明原因\n"
                "4. 如果没有新的内容要补充，可以简短表示\n\n"
                "请直接输出你的回应，不要加前缀。"
            )
        messages.append(Message(role=MessageRole.USER, content=instruction))

        # Generate response
        response = await self.llm.chat(
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        # Parse response
        content = response.content.strip()
        self._opinions.append(content)

        # Determine if agent wants to continue
        wants_to_continue = self._should_continue(content, phase)

        return AgentResponse(
            content=content,
            confidence=0.8,  # Could be parsed from response
            wants_to_continue=wants_to_continue,
            metadata={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )

    def _should_continue(self, content: str, phase: str) -> bool:
        """Determine if agent wants to continue the discussion."""
        # Simple heuristic: check for phrases indicating completion
        completion_phrases = [
            "没有补充",
            "没有更多",
            "我同意",
            "我赞同",
            "没有异议",
            "就这些",
        ]
        content_lower = content.lower()
        for phrase in completion_phrases:
            if phrase in content_lower:
                return False
        return True

    def reset(self):
        """Reset agent state for a new discussion."""
        self._conversation_history.clear()
        self._opinions.clear()
