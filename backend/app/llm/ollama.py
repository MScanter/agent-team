"""
Ollama LLM provider implementation for local models.
"""

from typing import AsyncIterator, Optional

import httpx

from app.llm.base import (
    LLMProvider,
    LLMResponse,
    Message,
    Tool,
    TokenPricing,
    TokenUsage,
)


class OllamaProvider(LLMProvider):
    """Ollama API provider for local models."""

    def __init__(
        self,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434",
    ):
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=120.0)

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def max_context_length(self) -> int:
        # Default context length, varies by model
        return 8192

    @property
    def supports_tools(self) -> bool:
        # Some Ollama models support tools, but not all
        return False

    @property
    def supports_vision(self) -> bool:
        # Some models like llava support vision
        return "llava" in self._model.lower()

    def get_pricing(self) -> TokenPricing:
        # Local models are free
        return TokenPricing(input_price_per_1k=0.0, output_price_per_1k=0.0)

    def count_tokens(self, text: str) -> int:
        # Approximate token count
        return len(text) // 4

    async def chat(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[list[Tool]] = None,
        **kwargs,
    ) -> LLMResponse:
        payload = {
            "model": self._model,
            "messages": [m.to_dict() for m in messages],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        response = await self._client.post(
            f"{self._base_url}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        return LLMResponse(
            content=data["message"]["content"],
            usage=TokenUsage(
                input_tokens=data.get("prompt_eval_count", 0),
                output_tokens=data.get("eval_count", 0),
            ),
            model=self._model,
            finish_reason="stop",
            raw_response=data,
        )

    async def stream(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> AsyncIterator[str]:
        payload = {
            "model": self._model,
            "messages": [m.to_dict() for m in messages],
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with self._client.stream(
            "POST",
            f"{self._base_url}/api/chat",
            json=payload,
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    import json

                    data = json.loads(line)
                    if "message" in data and "content" in data["message"]:
                        yield data["message"]["content"]

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
