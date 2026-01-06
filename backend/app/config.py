"""
Application configuration management.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

@dataclass(frozen=True)
class Settings:
    """Application settings (code-only; no environment variables)."""

    # Application
    app_name: str = "Agent Team"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8080

    # LLM Providers (only used by optional providers, not OpenAI-compatible)
    anthropic_api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"

    # Default model settings (used as fallback defaults)
    default_model: str = "gpt-4o-mini"
    default_temperature: float = 0.7
    default_max_tokens: int = 2048


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
