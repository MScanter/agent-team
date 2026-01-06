"""
OpenAI LLM provider implementation.
"""

from typing import AsyncIterator, Optional

import openai
from openai import AsyncOpenAI

from app.llm.base import (
    LLMProvider,
    LLMResponse,
    Message,
    Tool,
    TokenPricing,
    TokenUsage,
)


# Model configurations
OPENAI_MODELS = {
    "gpt-4o": {
        "max_context": 128000,
        "input_price": 0.0025,
        "output_price": 0.01,
        "supports_tools": True,
        "supports_vision": True,
    },
    "gpt-4o-mini": {
        "max_context": 128000,
        "input_price": 0.00015,
        "output_price": 0.0006,
        "supports_tools": True,
        "supports_vision": True,
    },
    "gpt-4-turbo": {
        "max_context": 128000,
        "input_price": 0.01,
        "output_price": 0.03,
        "supports_tools": True,
        "supports_vision": True,
    },
    "gpt-3.5-turbo": {
        "max_context": 16385,
        "input_price": 0.0005,
        "output_price": 0.0015,
        "supports_tools": True,
        "supports_vision": False,
    },
}


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
    ):
        self._model = model
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=60.0,
            max_retries=1,
        )
        self._config = OPENAI_MODELS.get(model, OPENAI_MODELS["gpt-4o-mini"])

    @property
    def provider_name(self) -> str:
        return "openai"

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
        # Approximate token count (4 chars per token for English)
        # For accurate counting, use tiktoken library
        return len(text) // 4

    async def chat(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[list[Tool]] = None,
        **kwargs,
    ) -> LLMResponse:
        request_kwargs = {
            "model": self._model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        if tools and self.supports_tools:
            request_kwargs["tools"] = [t.to_dict() for t in tools]

        response = await self._client.chat.completions.create(**request_kwargs)

        choice = response.choices[0]
        tool_calls = None
        if choice.message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in choice.message.tool_calls
            ]

        return LLMResponse(
            content=choice.message.content or "",
            usage=TokenUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            ),
            model=response.model,
            finish_reason=choice.finish_reason,
            tool_calls=tool_calls,
            raw_response=response,
        )

    async def stream(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> AsyncIterator[str]:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[m.to_dict() for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )

        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
