"""
Team management API routes (single-user, no auth, no database).
"""

import math
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status, Depends

from app.schemas.team import (
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamListResponse,
    TeamMemberCreate,
    TeamMemberResponse,
)
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.services.team_service import TeamService
from app.store import get_store, LOCAL_USER_ID, Store


router = APIRouter()


@router.get("", response_model=PaginatedResponse[TeamListResponse])
async def list_teams(
    store: Store = Depends(get_store),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    collaboration_mode: Optional[str] = None,
    is_template: Optional[bool] = None,
):
    service = TeamService(store)
    teams, total = service.list(
        user_id=LOCAL_USER_ID,
        page=page,
        page_size=page_size,
        search=search,
        collaboration_mode=collaboration_mode,
        is_template=is_template,
    )

    items = [
        TeamListResponse(
            id=t["id"],
            name=t["name"],
            description=t.get("description"),
            icon=t.get("icon"),
            collaboration_mode=t.get("collaboration_mode"),
            member_count=len(t.get("members") or []),
            is_template=bool(t.get("is_template")),
            is_public=bool(t.get("is_public")),
            usage_count=int(t.get("usage_count") or 0),
            rating=float(t.get("rating") or 0.0),
            created_at=t["created_at"],
        )
        for t in teams
    ]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: TeamCreate,
    store: Store = Depends(get_store),
):
    service = TeamService(store)
    team = service.create(LOCAL_USER_ID, team_data)
    return TeamResponse.model_validate(team)


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: str,
    store: Store = Depends(get_store),
):
    service = TeamService(store)
    team = service.get(team_id, LOCAL_USER_ID)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team {team_id} not found")
    return TeamResponse.model_validate(team)


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: str,
    team_data: TeamUpdate,
    store: Store = Depends(get_store),
):
    service = TeamService(store)
    team = service.update(team_id, LOCAL_USER_ID, team_data)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team {team_id} not found")
    return TeamResponse.model_validate(team)


@router.delete("/{team_id}", response_model=SuccessResponse)
async def delete_team(
    team_id: str,
    store: Store = Depends(get_store),
):
    service = TeamService(store)
    success = service.delete(team_id, LOCAL_USER_ID)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team {team_id} not found")
    return SuccessResponse(message="Team deleted successfully")


@router.post("/{team_id}/members", response_model=TeamMemberResponse)
async def add_team_member(
    team_id: str,
    member_data: TeamMemberCreate,
    store: Store = Depends(get_store),
):
    service = TeamService(store)
    member = service.add_member(team_id, LOCAL_USER_ID, member_data)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team or agent not found")
    return TeamMemberResponse.model_validate(member)


@router.delete("/{team_id}/members/{agent_id}", response_model=SuccessResponse)
async def remove_team_member(
    team_id: str,
    agent_id: str,
    store: Store = Depends(get_store),
):
    service = TeamService(store)
    success = service.remove_member(team_id, agent_id, LOCAL_USER_ID)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team or member not found")
    return SuccessResponse(message="Member removed successfully")


@router.post("/{team_id}/members/reorder", response_model=SuccessResponse)
async def reorder_team_members(
    team_id: str,
    agent_ids: list[str],
    store: Store = Depends(get_store),
):
    service = TeamService(store)
    try:
        success = service.reorder_members(team_id, LOCAL_USER_ID, agent_ids)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team {team_id} not found")
    return SuccessResponse(message="Members reordered successfully")


@router.post("/{team_id}/duplicate", response_model=TeamResponse)
async def duplicate_team(
    team_id: str,
    store: Store = Depends(get_store),
    new_name: Optional[str] = None,
):
    service = TeamService(store)
    team = service.duplicate(team_id, LOCAL_USER_ID, new_name)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Team {team_id} not found")
    return TeamResponse.model_validate(team)

