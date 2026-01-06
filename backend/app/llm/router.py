"""
Model router for intelligent model selection.
"""

from typing import Optional

from app.llm.base import LLMProvider
from app.llm.openai_compatible import OpenAICompatibleProvider


class ModelRouter:
    """
    Intelligent model router that selects the best model based on task requirements.
    """

    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}

    def _get_or_create_provider(
        self,
        provider_name: str,
        model_id: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        input_price_per_1k: float = 0.0,
        output_price_per_1k: float = 0.0,
        max_context_length: int = 8192,
        supports_tools: bool = True,
        supports_vision: bool = False,
    ) -> LLMProvider:
        """Get or create a provider instance."""
        resolved_base_url = base_url or "https://api.openai.com/v1"
        if not api_key:
            raise ValueError("No API key configured. Provide `llm` in ExecutionCreate (client-side configuration).")

        cache_key = f"{provider_name}:{model_id}:{hash(api_key)}:{resolved_base_url}"

        if cache_key not in self._providers:
            if provider_name in ("openai", "openai_compatible", "custom"):
                self._providers[cache_key] = OpenAICompatibleProvider(
                    api_key=api_key,
                    model=model_id,
                    base_url=resolved_base_url,
                    input_price_per_1k=input_price_per_1k,
                    output_price_per_1k=output_price_per_1k,
                    max_context_length=max_context_length,
                    supports_tools=supports_tools,
                    supports_vision=supports_vision,
                )
            else:
                raise ValueError(f"Unknown provider: {provider_name}")

        return self._providers[cache_key]

    def get_provider(
        self,
        provider_name: Optional[str] = None,
        model_id: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        input_price_per_1k: float = 0.0,
        output_price_per_1k: float = 0.0,
        max_context_length: int = 8192,
        supports_tools: bool = True,
        supports_vision: bool = False,
    ) -> LLMProvider:
        """
        Get a specific provider or the default one.

        Args:
            provider_name: Provider name (openai, anthropic, ollama, custom)
            model_id: Specific model ID
            api_key: API key for custom providers
            base_url: Base URL for custom providers
            input_price_per_1k: Price per 1K input tokens
            output_price_per_1k: Price per 1K output tokens
            max_context_length: Maximum context length
            supports_tools: Whether model supports tools
            supports_vision: Whether model supports vision

        Returns:
            LLMProvider instance
        """
        if provider_name and model_id:
            return self._get_or_create_provider(
                provider_name, model_id, api_key, base_url,
                input_price_per_1k, output_price_per_1k,
                max_context_length, supports_tools, supports_vision
            )

        raise ValueError("LLM provider not configured. Provide provider_name/model_id/api_key at runtime.")

    def route(
        self,
        task_type: str = "general",
        content_length: int = 0,
        requires_tools: bool = False,
        budget_sensitive: bool = False,
    ) -> LLMProvider:
        """
        Intelligently route to the best model based on task requirements.

        Args:
            task_type: Type of task (summary, analysis, creative, general)
            content_length: Approximate input content length in tokens
            requires_tools: Whether the task requires tool/function calling
            budget_sensitive: Whether to prioritize cost savings

        Returns:
            Best suited LLMProvider for the task
        """
        # For now, return the default provider
        # In a real implementation, you might want to have different models
        # based on the task type, but all would be OpenAI-compatible
        return self.get_provider()


# Global router instance
_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    """Get the global model router instance."""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
