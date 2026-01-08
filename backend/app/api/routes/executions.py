"""
Execution management API routes (single-user, no auth, no database).
"""

import asyncio
import json
import math
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status, Depends, WebSocket, WebSocketDisconnect

from app.schemas.execution import (
    ExecutionCreate,
    ExecutionResponse,
    ExecutionListResponse,
    ExecutionControl,
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

@router.websocket("/{execution_id}/ws")
async def execution_ws(
    websocket: WebSocket,
    execution_id: str,
    store: Store = Depends(get_store),
):
    await websocket.accept()
    service = ExecutionService(store)
    execution = service.get(execution_id, LOCAL_USER_ID)
    if not execution:
        await websocket.send_text(
            json.dumps(
                {"event_type": "error", "data": {"message": f"Execution {execution_id} not found"}},
                ensure_ascii=False,
            )
        )
        await websocket.close()
        return

    async def send_event(event):
        await websocket.send_text(
            json.dumps(
                {
                    "event_type": event.event_type,
                    "data": event.data,
                    "agent_id": event.agent_id,
                    "sequence": event.sequence,
                },
                ensure_ascii=False,
            )
        )

    last_seen = time.monotonic()
    heartbeat_timeout = 60.0

    await websocket.send_text(
        json.dumps({"event_type": "connected", "data": {"execution_id": execution_id}}, ensure_ascii=False)
    )

    if execution.get("status") == "pending":
        async for event in service.start(execution_id, LOCAL_USER_ID):
            await send_event(event)
    else:
        await websocket.send_text(
            json.dumps({"event_type": "status", "data": {"status": execution.get("status")}}, ensure_ascii=False)
        )

    try:
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=heartbeat_timeout)
            except asyncio.TimeoutError:
                if time.monotonic() - last_seen >= heartbeat_timeout:
                    await websocket.close()
                    break
                continue

            last_seen = time.monotonic()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"event_type": "error", "data": {"message": "Invalid JSON payload"}}, ensure_ascii=False)
                )
                continue

            msg_type = payload.get("type")
            if msg_type == "followup":
                input_text = str(payload.get("input") or "").strip()
                if not input_text:
                    await websocket.send_text(
                        json.dumps(
                            {"event_type": "error", "data": {"message": "Follow-up input required"}},
                            ensure_ascii=False,
                        )
                    )
                    continue
                target_agent_id = payload.get("target_agent_id")
                async for event in service.followup(execution_id, LOCAL_USER_ID, input_text, target_agent_id):
                    await send_event(event)
                await websocket.send_text(
                    json.dumps({"event_type": "status", "data": {"status": "completed"}}, ensure_ascii=False)
                )
            elif msg_type == "start":
                execution = service.get(execution_id, LOCAL_USER_ID)
                if execution and execution.get("status") == "pending":
                    async for event in service.start(execution_id, LOCAL_USER_ID):
                        await send_event(event)
            elif msg_type == "control":
                action = payload.get("action")
                params = payload.get("params") if isinstance(payload.get("params"), dict) else None
                if not action or not service.control(execution_id, LOCAL_USER_ID, action, params):
                    await websocket.send_text(
                        json.dumps(
                            {"event_type": "error", "data": {"message": "Invalid control action"}},
                            ensure_ascii=False,
                        )
                    )
            elif msg_type in {"ping", "pong"}:
                await websocket.send_text(json.dumps({"event_type": "pong", "data": {}}, ensure_ascii=False))
            else:
                await websocket.send_text(
                    json.dumps({"event_type": "error", "data": {"message": "Unknown message type"}}, ensure_ascii=False)
                )
    except WebSocketDisconnect:
        return


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
