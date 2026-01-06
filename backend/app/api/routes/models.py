"""
Model configuration API routes (single-user, no auth, no database).
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status, Depends
from pydantic import BaseModel, Field

from app.schemas.common import SuccessResponse
from app.services.llm_service import get_provider_for_model_config
from app.store import get_store, LOCAL_USER_ID, Store


router = APIRouter()


class ModelConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    provider: str = Field(..., pattern="^openai_compatible$")
    model_id: str = Field(..., min_length=1, max_length=100)
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class ModelConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    provider: Optional[str] = Field(None, pattern="^openai_compatible$")
    model_id: Optional[str] = Field(None, min_length=1, max_length=100)
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class ModelConfigResponse(ModelConfigCreate):
    id: str
    user_id: Optional[str]
    is_active: bool
    is_default: bool
    created_at: str
    updated_at: str


def _to_response(record: dict) -> ModelConfigResponse:
    return ModelConfigResponse(
        id=record["id"],
        user_id=record.get("user_id"),
        name=record["name"],
        description=record.get("description"),
        provider=record["provider"],
        model_id=record["model_id"],
        api_key=None,
        base_url=record.get("base_url"),
        is_active=bool(record.get("is_active", True)),
        is_default=bool(record.get("is_default", False)),
        created_at=record["created_at"].isoformat(),
        updated_at=record["updated_at"].isoformat(),
    )


@router.get("", response_model=list[ModelConfigResponse])
async def list_models(
    store: Store = Depends(get_store),
    include_system: bool = Query(True, description="Include system presets"),
):
    configs: list[ModelConfigResponse] = []
    if include_system:
        configs.append(
            ModelConfigResponse(
                id="openai-compatible",
                user_id=None,
                name="OpenAI Compatible",
                description="通用OpenAI兼容API",
                provider="openai_compatible",
                model_id="gpt-4o",
                api_key=None,
                base_url=None,
                is_active=True,
                is_default=True,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            )
        )

    for record in store.model_configs.values():
        if record.get("user_id") == LOCAL_USER_ID:
            configs.append(_to_response(record))

    return configs


@router.post("", response_model=ModelConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_model_config(
    config: ModelConfigCreate,
    store: Store = Depends(get_store),
):
    config_id = store.new_id()
    record = {
        "id": config_id,
        "user_id": LOCAL_USER_ID,
        "name": config.name,
        "description": config.description,
        "provider": config.provider,
        "model_id": config.model_id,
        "api_key": config.api_key,
        "base_url": config.base_url,
        "max_context_length": 8192,
        "supports_tools": True,
        "supports_vision": False,
        "is_active": True,
        "is_default": False,
    }
    store.touch(record, created=True)
    store.model_configs[config_id] = record
    return _to_response(record)


@router.get("/{config_id}", response_model=ModelConfigResponse)
async def get_model_config(
    config_id: str,
    store: Store = Depends(get_store),
):
    record = store.model_configs.get(config_id)
    if not record or record.get("user_id") != LOCAL_USER_ID:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Model config {config_id} not found")
    return _to_response(record)


@router.put("/{config_id}", response_model=ModelConfigResponse)
async def update_model_config(
    config_id: str,
    config_update: ModelConfigUpdate,
    store: Store = Depends(get_store),
):
    record = store.model_configs.get(config_id)
    if not record or record.get("user_id") != LOCAL_USER_ID:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Model config {config_id} not found")

    update_data = config_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "api_key" and (value is None or value == ""):
            continue
        record[field] = value

    store.touch(record)
    return _to_response(record)


@router.delete("/{config_id}", response_model=SuccessResponse)
async def delete_model_config(
    config_id: str,
    store: Store = Depends(get_store),
):
    record = store.model_configs.get(config_id)
    if not record or record.get("user_id") != LOCAL_USER_ID:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Model config {config_id} not found")

    store.model_configs.pop(config_id, None)
    return SuccessResponse(message="Model configuration deleted successfully")


@router.post("/{config_id}/test")
async def test_model_config(
    config_id: str,
    store: Store = Depends(get_store),
    test_message: str = Query("Hello, can you hear me?"),
):
    record = store.model_configs.get(config_id)
    if not record or record.get("user_id") != LOCAL_USER_ID:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Model config {config_id} not found")

    try:
        provider = await get_provider_for_model_config(record)
        from app.llm.base import Message, MessageRole

        messages = [Message(role=MessageRole.USER, content=test_message)]
        response = await provider.chat(messages, max_tokens=50)
        return {
            "message": f"Test successful for model {record['name']}",
            "config_id": config_id,
            "response_preview": response.content[:100] + "..." if len(response.content) > 100 else response.content,
            "tokens_used": response.usage.total_tokens,
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Test failed: {str(e)}")

