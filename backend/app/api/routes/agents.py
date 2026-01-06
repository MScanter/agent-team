"""
Agent management API routes (single-user, no auth, no database).
"""

import math
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status, Depends

from app.schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentListResponse,
    AgentFromTemplate,
)
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.services.agent_service import AgentService
from app.store import get_store, LOCAL_USER_ID, Store


router = APIRouter()


@router.get("", response_model=PaginatedResponse[AgentListResponse])
async def list_agents(
    store: Store = Depends(get_store),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    tags: Optional[str] = None,
    is_template: Optional[bool] = None,
    collaboration_style: Optional[str] = None,
):
    service = AgentService(store)
    tags_list = tags.split(",") if tags else None

    agents, total = service.list(
        user_id=LOCAL_USER_ID,
        page=page,
        page_size=page_size,
        search=search,
        tags=tags_list,
        is_template=is_template,
        collaboration_style=collaboration_style,
    )

    return PaginatedResponse(
        items=[AgentListResponse.model_validate(a) for a in agents],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    store: Store = Depends(get_store),
):
    service = AgentService(store)

    agent = service.create(LOCAL_USER_ID, agent_data)
    return AgentResponse.model_validate(agent)


@router.get("/templates", response_model=list[AgentListResponse])
async def list_templates(
    store: Store = Depends(get_store),
    category: Optional[str] = None,
):
    service = AgentService(store)
    templates = service.get_templates(category)
    return [AgentListResponse.model_validate(t) for t in templates]


@router.post("/from-template", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_from_template(
    data: AgentFromTemplate,
    store: Store = Depends(get_store),
):
    service = AgentService(store)
    agent = service.create_from_template(
        template_id=data.template_id,
        user_id=LOCAL_USER_ID,
        name=data.name,
        customizations=data.customizations,
    )

    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    return AgentResponse.model_validate(agent)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    store: Store = Depends(get_store),
):
    service = AgentService(store)
    agent = service.get(agent_id, LOCAL_USER_ID)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")
    return AgentResponse.model_validate(agent)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    agent_data: AgentUpdate,
    store: Store = Depends(get_store),
):
    service = AgentService(store)

    agent = service.update(agent_id, LOCAL_USER_ID, agent_data)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")
    return AgentResponse.model_validate(agent)


@router.delete("/{agent_id}", response_model=SuccessResponse)
async def delete_agent(
    agent_id: str,
    store: Store = Depends(get_store),
):
    service = AgentService(store)
    success = service.delete(agent_id, LOCAL_USER_ID)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")
    return SuccessResponse(message="Agent deleted successfully")


@router.post("/{agent_id}/duplicate", response_model=AgentResponse)
async def duplicate_agent(
    agent_id: str,
    store: Store = Depends(get_store),
    new_name: Optional[str] = None,
):
    service = AgentService(store)
    agent = service.duplicate(agent_id, LOCAL_USER_ID, new_name)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found")
    return AgentResponse.model_validate(agent)
