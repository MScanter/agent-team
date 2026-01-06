"""
OpenAI Compatible LLM provider implementation.
This allows users to connect to any OpenAI-compatible API endpoint.
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


class OpenAICompatibleProvider(LLMProvider):
    """
    OpenAI Compatible API provider.
    Allows users to connect to any OpenAI-compatible API endpoint.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        input_price_per_1k: float = 0.0,
        output_price_per_1k: float = 0.0,
        max_context_length: int = 8192,
        supports_tools: bool = True,
        supports_vision: bool = False,
    ):
        self._model = model
        self._base_url = base_url
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=60.0,
            max_retries=1,
            default_headers={
                # Use a realistic browser User-Agent to avoid WAF blocks.
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "application/json",
            },
        )
        
        # Configuration from user input
        self._input_price_per_1k = input_price_per_1k
        self._output_price_per_1k = output_price_per_1k
        self._max_context_length = max_context_length
        self._supports_tools = supports_tools
        self._supports_vision = supports_vision

    @property
    def provider_name(self) -> str:
        return "custom"

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def max_context_length(self) -> int:
        return self._max_context_length

    @property
    def supports_tools(self) -> bool:
        return self._supports_tools

    @property
    def supports_vision(self) -> bool:
        return self._supports_vision

    def get_pricing(self) -> TokenPricing:
        return TokenPricing(
            input_price_per_1k=self._input_price_per_1k,
            output_price_per_1k=self._output_price_per_1k,
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
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
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
