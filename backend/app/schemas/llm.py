"""
LLM configuration schemas for runtime (single-user, no auth, no database).
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class OpenAICompatibleRuntimeConfig(BaseModel):
    """Runtime config for any OpenAI-compatible API."""

    provider: Literal["openai_compatible"] = "openai_compatible"
    model_id: str = Field(..., min_length=1, max_length=100)
    api_key: str = Field(..., min_length=1, description="API key for the provider")
    base_url: Optional[str] = Field(
        default=None,
        description="OpenAI-compatible base URL (should include /v1)",
    )

    # Optional capabilities metadata (used for routing/UI; defaults match existing behavior)
    max_context_length: int = Field(default=8192, ge=1)
    supports_tools: bool = True
    supports_vision: bool = False

    # Optional pricing metadata
    input_price_per_1k: float = Field(default=0.0, ge=0)
    output_price_per_1k: float = Field(default=0.0, ge=0)


class ExecutionLLMConfig(BaseModel):
    """
    LLM config bundle attached to an execution.

    - `default` is used when an agent has no `model_id`, or when `model_id` is a raw model name.
    - `models` is a mapping from client-side model-config IDs to runtime configs.
    """

    default: OpenAICompatibleRuntimeConfig
    models: dict[str, OpenAICompatibleRuntimeConfig] = Field(default_factory=dict)

