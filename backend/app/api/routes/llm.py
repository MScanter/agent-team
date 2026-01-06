"""
LLM utility API routes (single-user, no auth, no database).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

import openai
from app.llm.base import Message, MessageRole
from app.schemas.llm import OpenAICompatibleRuntimeConfig
from app.services.llm_service import get_provider_for_model_config, _normalize_openai_compatible_base_url


router = APIRouter()


class TestLLMRequest(BaseModel):
    config: OpenAICompatibleRuntimeConfig
    test_message: str = Field(default="Hello, can you hear me?", min_length=1)


@router.post("/test")
async def test_llm(req: TestLLMRequest):
    try:
        resolved_base_url = _normalize_openai_compatible_base_url(req.config.base_url)
        provider = await get_provider_for_model_config(req.config.model_dump())
        messages = [Message(role=MessageRole.USER, content=req.test_message)]
        response = await provider.chat(messages, max_tokens=50)
        return {
            "message": f"Test successful for model {req.config.model_id}",
            "response_preview": response.content[:100] + "..." if len(response.content) > 100 else response.content,
            "tokens_used": response.usage.total_tokens,
            "resolved_base_url": resolved_base_url,
        }
    except openai.APIConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Connection to provider failed",
                "error": str(e),
                "base_url": req.config.base_url,
                "resolved_base_url": _normalize_openai_compatible_base_url(req.config.base_url),
                "model_id": req.config.model_id,
                "hint": "Check base_url (including /v1), network connectivity, and whether the provider is reachable from the backend.",
            },
        )
    except openai.APIStatusError as e:
        upstream_status = getattr(e, "status_code", None) or getattr(getattr(e, "response", None), "status_code", None)
        upstream_body = None
        upstream_headers = None
        try:
            upstream_body = getattr(getattr(e, "response", None), "text", None)
        except Exception:
            upstream_body = None

        try:
            headers_obj = getattr(getattr(e, "response", None), "headers", None)
            if headers_obj:
                # Return a small allowlist to help diagnose WAF/CDN blocks without leaking anything sensitive.
                allow = {
                    "date",
                    "server",
                    "content-type",
                    "content-length",
                    "cf-ray",
                    "cf-cache-status",
                    "x-request-id",
                    "x-amzn-requestid",
                    "x-amz-cf-id",
                    "x-amz-cf-pop",
                    "via",
                }
                upstream_headers = {k: v for k, v in dict(headers_obj).items() if k.lower() in allow}
        except Exception:
            upstream_headers = None

        if isinstance(upstream_body, str) and len(upstream_body) > 1200:
            upstream_body = upstream_body[:1200] + "…"

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Provider returned an error response",
                "upstream_status": upstream_status,
                "upstream_body": upstream_body,
                "upstream_headers": upstream_headers,
                "error": str(e),
                "base_url": req.config.base_url,
                "resolved_base_url": _normalize_openai_compatible_base_url(req.config.base_url),
                "model_id": req.config.model_id,
                "hint": "If upstream_status is 401/403, check API key/permissions/WAF blocks; if 404, check base_url and model_id.",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Test failed: {str(e)}")
