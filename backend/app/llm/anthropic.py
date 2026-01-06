"""
Anthropic Claude LLM provider implementation.
"""

from typing import AsyncIterator, Optional

from anthropic import AsyncAnthropic

from app.llm.base import (
    LLMProvider,
    LLMResponse,
    Message,
    MessageRole,
    Tool,
    TokenPricing,
    TokenUsage,
)


# Model configurations
ANTHROPIC_MODELS = {
    "claude-3-5-sonnet-20241022": {
        "max_context": 200000,
        "input_price": 0.003,
        "output_price": 0.015,
        "supports_tools": True,
        "supports_vision": True,
    },
    "claude-3-5-haiku-20241022": {
        "max_context": 200000,
        "input_price": 0.001,
        "output_price": 0.005,
        "supports_tools": True,
        "supports_vision": True,
    },
    "claude-3-opus-20240229": {
        "max_context": 200000,
        "input_price": 0.015,
        "output_price": 0.075,
        "supports_tools": True,
        "supports_vision": True,
    },
}


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
    ):
        self._model = model
        self._client = AsyncAnthropic(api_key=api_key)
        self._config = ANTHROPIC_MODELS.get(
            model, ANTHROPIC_MODELS["claude-3-5-sonnet-20241022"]
        )

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def max_context_length(self) -> int:
        return self._config["max_context"]

    @property
    def supports_tools(self) -> bool:
        return self._config.get("supports_tools", False)

    @property
    def supports_vision(self) -> bool:
        return self._config.get("supports_vision", False)

    def get_pricing(self) -> TokenPricing:
        return TokenPricing(
            input_price_per_1k=self._config["input_price"],
            output_price_per_1k=self._config["output_price"],
        )

    def count_tokens(self, text: str) -> int:
        # Approximate token count
        return len(text) // 4

    def _convert_messages(
        self, messages: list[Message]
    ) -> tuple[Optional[str], list[dict]]:
        """Convert messages to Anthropic format, extracting system message."""
        system_message = None
        converted = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_message = msg.content
            else:
                role = "user" if msg.role == MessageRole.USER else "assistant"
                converted.append({"role": role, "content": msg.content})

        return system_message, converted

    def _convert_tools(self, tools: list[Tool]) -> list[dict]:
        """Convert tools to Anthropic format."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            }
            for t in tools
        ]

    async def chat(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[list[Tool]] = None,
        **kwargs,
    ) -> LLMResponse:
        system_message, converted_messages = self._convert_messages(messages)

        request_kwargs = {
            "model": self._model,
            "messages": converted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }

        if system_message:
            request_kwargs["system"] = system_message

        if tools and self.supports_tools:
            request_kwargs["tools"] = self._convert_tools(tools)

        response = await self._client.messages.create(**request_kwargs)

        # Extract text content
        content = ""
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    {
                        "id": block.id,
                        "type": "function",
                        "function": {
                            "name": block.name,
                            "arguments": str(block.input),
                        },
                    }
                )

        return LLMResponse(
            content=content,
            usage=TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
            model=response.model,
            finish_reason=response.stop_reason,
            tool_calls=tool_calls if tool_calls else None,
            raw_response=response,
        )

    async def stream(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> AsyncIterator[str]:
        system_message, converted_messages = self._convert_messages(messages)

        request_kwargs = {
            "model": self._model,
            "messages": converted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }

        if system_message:
            request_kwargs["system"] = system_message

        async with self._client.messages.stream(**request_kwargs) as stream:
            async for text in stream.text_stream:
                yield text
