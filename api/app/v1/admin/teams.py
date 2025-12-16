import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies
from app._crud.admin.teams import add_team_member as crud_add_team_member
from app._crud.admin.teams import (
    create_team as crud_create_team,
)
from app._crud.admin.teams import delete_team as crud_delete_team
from app._crud.admin.teams import (
    get_teams as crud_get_teams,
)
from app._crud.admin.teams import (
    get_teams_with_members as crud_get_teams_with_members,
)
from app._crud.admin.teams import remove_team_member as crud_remove_team_member
from app._crud.admin.teams import rename_team as crud_rename_team
from app.interfaces import (
    Team,
    TeamCreate,
    TeamMemberAdd,
    TeamUpdate,
    TeamWithMembers,
    UserData,
)

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get(
    "",
    response_model=list[Team],
    dependencies=[Depends(dependencies.requires_admin_async)],
)
async def get_teams(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    company_id: uuid.UUID = Query(...),
):
    """todo

    Args:
        db: TODO: describe.
        company_id: TODO: describe.
    """
    return await crud_get_teams(db=db, company_id=company_id)


@router.get(
    "/company",
    response_model=list[Team],
)
async def get_company_teams(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[UserData, Depends(dependencies.get_user_data_async)],
):
    """Get teams for the current user's company. No admin required.

    Args:
        db: TODO: describe.
        user_data: TODO: describe.
    """
    return await crud_get_teams(db=db, company_id=user_data.company_id)


@router.get(
    "/company/members",
    response_model=list[TeamWithMembers],
)
async def get_company_teams_with_members(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[UserData, Depends(dependencies.get_user_data_async)],
):
    """Get teams with members for the current user's company. No admin required.

    Args:
        db: TODO: describe.
        user_data: TODO: describe.
    """
    return await crud_get_teams_with_members(db=db, company_id=user_data.company_id)


@router.post(
    "",
    response_model=Team,
    status_code=201,
    dependencies=[Depends(dependencies.requires_admin_async)],
)
async def create_team(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[UserData, Depends(dependencies.get_user_data_async)],
    team: TeamCreate,
):
    """todo

    Args:
        db: TODO: describe.
        user_data: TODO: describe.
        team: TODO: describe.
    """
    try:
        return await crud_create_team(db=db, company_id=user_data.company_id, team=team)
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Team with this name already exists for this company",
        )


@router.get(
    "/members",
    response_model=list[TeamWithMembers],
    dependencies=[Depends(dependencies.requires_admin_async)],
)
async def get_teams_with_members(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    company_id: uuid.UUID = Query(...),
):
    """todo

    Args:
        db: TODO: describe.
        company_id: TODO: describe.
    """
    return await crud_get_teams_with_members(db=db, company_id=company_id)


@router.post(
    "/{team_id}/members",
    status_code=204,
    dependencies=[Depends(dependencies.requires_admin_async)],
)
async def add_member(
    team_id: uuid.UUID,
    payload: TeamMemberAdd,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """todo

    Args:
        team_id: TODO: describe.
        payload: TODO: describe.
        db: TODO: describe.
    """
    await crud_add_team_member(db=db, team_id=team_id, user_id=payload.user_id)
    return


@router.delete(
    "/{team_id}/members/{user_id}",
    status_code=204,
    dependencies=[Depends(dependencies.requires_admin_async)],
)
async def remove_member(
    team_id: uuid.UUID,
    user_id: str,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """todo

    Args:
        team_id: TODO: describe.
        user_id: TODO: describe.
        db: TODO: describe.
    """
    await crud_remove_team_member(db=db, team_id=team_id, user_id=user_id)
    return


@router.delete(
    "/{team_id}",
    status_code=204,
    dependencies=[Depends(dependencies.requires_admin_async)],
)
async def delete_team(
    team_id: uuid.UUID, db: Annotated[AsyncSession, Depends(dependencies.get_async_db)]
):
    """todo

    Args:
        team_id: TODO: describe.
        db: TODO: describe.
    """
    await crud_delete_team(db=db, team_id=team_id)
    return


@router.patch(
    "/{team_id}",
    response_model=Team,
    dependencies=[Depends(dependencies.requires_admin_async)],
)
async def update_team(
    team_id: uuid.UUID,
    payload: TeamUpdate,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """todo

    Args:
        team_id: TODO: describe.
        payload: TODO: describe.
        db: TODO: describe.
    """
    try:
        return await crud_rename_team(db=db, team_id=team_id, payload=payload)
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Team with this name already exists for this company",
        )
