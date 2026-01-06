"""
LLM Provider base class and common types.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Optional


class MessageRole(str, Enum):
    """Message role in conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """Chat message."""

    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[list[dict]] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for API calls."""
        data = {"role": self.role.value, "content": self.content}
        if self.name:
            data["name"] = self.name
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            data["tool_calls"] = self.tool_calls
        return data


@dataclass
class TokenUsage:
    """Token usage statistics."""

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class TokenPricing:
    """Token pricing per 1K tokens."""

    input_price_per_1k: float
    output_price_per_1k: float

    def calculate_cost(self, usage: TokenUsage) -> float:
        """Calculate cost for given token usage."""
        input_cost = (usage.input_tokens / 1000) * self.input_price_per_1k
        output_cost = (usage.output_tokens / 1000) * self.output_price_per_1k
        return input_cost + output_cost


@dataclass
class LLMResponse:
    """Response from LLM provider."""

    content: str
    usage: TokenUsage
    model: str
    finish_reason: Optional[str] = None
    tool_calls: Optional[list[dict]] = None
    raw_response: Optional[Any] = None


@dataclass
class Tool:
    """Tool definition for function calling."""

    name: str
    description: str
    parameters: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider name identifier."""
        pass

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Model identifier."""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[list[Tool]] = None,
        **kwargs,
    ) -> LLMResponse:
        """Send chat completion request."""
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream chat completion response."""
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        pass

    @abstractmethod
    def get_pricing(self) -> TokenPricing:
        """Get token pricing for this model."""
        pass

    @property
    @abstractmethod
    def max_context_length(self) -> int:
        """Maximum context length supported by the model."""
        pass

    @property
    def supports_tools(self) -> bool:
        """Whether this model supports tool/function calling."""
        return False

    @property
    def supports_vision(self) -> bool:
        """Whether this model supports vision/image input."""
        return False
