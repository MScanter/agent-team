"""
LLM provider selection for the in-memory Store (single-user, no database).
"""

from __future__ import annotations

from typing import Optional

from app.llm.base import LLMProvider
from app.llm.router import get_model_router
from app.store import Store


def _looks_like_client_config_id(value: str) -> bool:
    # crypto.randomUUID() style, plus our fallback "mc_*" ids.
    if value.startswith("mc_"):
        return True
    parts = value.split("-")
    if len(parts) != 5:
        return False
    return all(parts) and all(len(p) in (8, 4, 4, 4, 12) for p in parts)


def _normalize_openai_compatible_base_url(base_url: Optional[str]) -> Optional[str]:
    if base_url is None:
        return None
    base_url = base_url.strip()
    if not base_url:
        return None
    # Normalize common input mistakes:
    # - Users sometimes paste the full endpoint path (/v1/chat/completions); OpenAI SDK expects the base URL.
    if base_url.rstrip("/").endswith("/chat/completions"):
        base_url = base_url.rstrip("/")
        base_url = base_url[: -len("/chat/completions")]

    # Only auto-append /v1 when the URL has no path. If the user provides a path,
    # respect it as-is because some providers mount the OpenAI endpoints under a custom prefix.
    from urllib.parse import urlparse

    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        return base_url.rstrip("/")

    path = parsed.path or ""
    if path in ("", "/"):
        return f"{base_url.rstrip('/')}/v1"

    if base_url.endswith("/v1/"):
        return base_url[:-1]
    return base_url.rstrip("/")


async def get_provider_for_agent(store: Store, agent: dict, *, llm_config: Optional[dict] = None) -> LLMProvider:
    """
    Resolve the LLM provider for an agent.

    Behavior:
    - If `llm_config` is present on the execution, resolve from it first.
      - If agent.model_id matches a client-side config id, use that config.
      - Otherwise, treat agent.model_id as a raw model name and use `llm_config.default`.
      - If agent.model_id is unset, use `llm_config.default.model_id`.
    - Otherwise, fall back to server-side stored model configs (legacy).
    """
    model_ref = agent.get("model_id")

    if llm_config:
        models = llm_config.get("models") or {}
        if model_ref and model_ref in models:
            cfg = models.get(model_ref)
            if cfg and cfg.get("is_active", True):
                return await get_provider_for_model_config(cfg)

        default_cfg = llm_config.get("default")
        if not default_cfg:
            raise ValueError("No LLM configured. Please set it in the UI (API配置) and start a new execution.")

        cfg = dict(default_cfg)
        if model_ref and model_ref not in models:
            if _looks_like_client_config_id(model_ref):
                raise ValueError(
                    f"Agent model_id '{model_ref}' refers to a client-side model config, but it is not available "
                    "in this execution's `llm` bundle (missing or missing API key)."
                )
            cfg["model_id"] = model_ref
        return await get_provider_for_model_config(cfg)

    if model_ref:
        model_config = store.model_configs.get(model_ref)
        if model_config and model_config.get("is_active", True):
            return await get_provider_for_model_config(model_config)

    raise ValueError("No LLM configured for this execution. Provide `llm` in ExecutionCreate.")


async def get_provider_for_model_config(model_config: dict) -> LLMProvider:
    if not model_config.get("api_key"):
        raise ValueError("Model config is missing api_key")

    router = get_model_router()
    return router.get_provider(
        provider_name="custom",
        model_id=model_config["model_id"],
        api_key=model_config["api_key"],
        base_url=_normalize_openai_compatible_base_url(model_config.get("base_url")),
        max_context_length=model_config.get("max_context_length", 8192),
        supports_tools=model_config.get("supports_tools", True),
        supports_vision=model_config.get("supports_vision", False),
    )
