"""
Execution management API routes (single-user, no auth, no database).
"""

import json
import math
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status, Depends
from fastapi.responses import StreamingResponse

from app.schemas.execution import (
    ExecutionCreate,
    ExecutionResponse,
    ExecutionListResponse,
    ExecutionControl,
    ExecutionFollowUp,
    ExecutionMessageResponse,
)
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.services.execution_service import ExecutionService
from app.store import get_store, LOCAL_USER_ID, Store


router = APIRouter()


@router.get("", response_model=PaginatedResponse[ExecutionListResponse])
async def list_executions(
    store: Store = Depends(get_store),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    team_id: Optional[str] = None,
    status_filter: Optional[str] = None,
):
    service = ExecutionService(store)
    executions, total = service.list(
        user_id=LOCAL_USER_ID,
        page=page,
        page_size=page_size,
        team_id=team_id,
        status_filter=status_filter,
    )

    items = [
        ExecutionListResponse(
            id=e["id"],
            team_id=e.get("team_id"),
            title=e.get("title"),
            status=e.get("status"),
            current_round=e.get("current_round", 0),
            tokens_used=e.get("tokens_used", 0),
            cost=e.get("cost", 0.0),
            started_at=e.get("started_at"),
            completed_at=e.get("completed_at"),
            created_at=e["created_at"],
        )
        for e in executions
    ]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.post("", response_model=ExecutionResponse, status_code=status.HTTP_201_CREATED)
async def create_execution(
    execution_data: ExecutionCreate,
    store: Store = Depends(get_store),
):
    service = ExecutionService(store)
    try:
        execution = service.create(LOCAL_USER_ID, execution_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return ExecutionResponse.model_validate(execution)


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: str,
    store: Store = Depends(get_store),
):
    service = ExecutionService(store)
    execution = service.get(execution_id, LOCAL_USER_ID)
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Execution {execution_id} not found")

    messages = service.get_messages(execution_id, limit=50)
    response = ExecutionResponse.model_validate(execution)
    response.recent_messages = [ExecutionMessageResponse.model_validate(m) for m in messages]
    return response


@router.get("/{execution_id}/messages", response_model=list[ExecutionMessageResponse])
async def get_execution_messages(
    execution_id: str,
    store: Store = Depends(get_store),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    round_filter: Optional[int] = None,
    agent_id: Optional[str] = None,
):
    service = ExecutionService(store)
    execution = service.get(execution_id, LOCAL_USER_ID)
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Execution {execution_id} not found")

    messages = service.get_messages(
        execution_id,
        limit=limit,
        offset=offset,
        round_filter=round_filter,
        agent_id=agent_id,
    )
    return [ExecutionMessageResponse.model_validate(m) for m in messages]


@router.get("/{execution_id}/stream")
async def stream_execution(
    execution_id: str,
    store: Store = Depends(get_store),
):
    service = ExecutionService(store)
    execution = service.get(execution_id, LOCAL_USER_ID)
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Execution {execution_id} not found")

    async def event_generator():
        yield f"data: {json.dumps({'event_type': 'connected', 'data': {'execution_id': execution_id}})}\n\n"

        if execution.get("status") == "pending":
            async for event in service.start(execution_id, LOCAL_USER_ID):
                data = json.dumps(
                    {
                        "event_type": event.event_type,
                        "data": event.data,
                        "agent_id": event.agent_id,
                        "sequence": event.sequence,
                    },
                    ensure_ascii=False,
                )
                yield f"data: {data}\n\n"
        else:
            yield f"data: {json.dumps({'event_type': 'status', 'data': {'status': execution.get('status')}})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/{execution_id}/control", response_model=SuccessResponse)
async def control_execution(
    execution_id: str,
    control: ExecutionControl,
    store: Store = Depends(get_store),
):
    service = ExecutionService(store)
    success = service.control(execution_id, LOCAL_USER_ID, control.action, control.params)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action or execution state")
    return SuccessResponse(message=f"Action '{control.action}' executed successfully")


@router.post("/{execution_id}/followup")
async def followup_execution(
    execution_id: str,
    followup: ExecutionFollowUp,
    store: Store = Depends(get_store),
):
    service = ExecutionService(store)

    async def event_generator():
        async for event in service.followup(execution_id, LOCAL_USER_ID, followup.input, followup.target_agent_id):
            data = json.dumps(
                {
                    "event_type": event.event_type,
                    "data": event.data,
                    "agent_id": event.agent_id,
                    "sequence": event.sequence,
                },
                ensure_ascii=False,
            )
            yield f"data: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.delete("/{execution_id}", response_model=SuccessResponse)
async def delete_execution(
    execution_id: str,
    store: Store = Depends(get_store),
):
    service = ExecutionService(store)
    success = service.delete(execution_id, LOCAL_USER_ID)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Execution {execution_id} not found")
    return SuccessResponse(message="Execution deleted successfully")

