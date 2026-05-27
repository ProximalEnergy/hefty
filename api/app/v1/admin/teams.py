import uuid
from typing import Annotated, Any, cast

from core.db_query import OutputType
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies
from app._crud.admin.teams import (
    add_team_member as crud_add_team_member,
)
from app._crud.admin.teams import (
    create_team as crud_create_team,
)
from app._crud.admin.teams import (
    delete_team as crud_delete_team,
)
from app._crud.admin.teams import (
    delete_team_assignments as crud_delete_team_assignments,
)
from app._crud.admin.teams import (
    delete_team_members as crud_delete_team_members,
)
from app._crud.admin.teams import (
    get_admin_team_user,
    get_team_members_for_teams,
)
from app._crud.admin.teams import (
    get_team as crud_get_team,
)
from app._crud.admin.teams import (
    get_teams as crud_get_teams,
)
from app._crud.admin.teams import (
    remove_team_member as crud_remove_team_member,
)
from app._crud.admin.teams import (
    rename_team as crud_rename_team,
)
from app._dependencies.authentication import get_user
from app.interfaces import (
    TeamCreate,
    TeamInterface,
    TeamMemberAdd,
    TeamUpdate,
    TeamWithMembers,
    UserAuthed,
    UserBasic,
)
from core import models

router = APIRouter(prefix="/teams", tags=["teams"])


async def _build_teams_with_members(
    *, db: AsyncSession, company_id: uuid.UUID
) -> list[TeamWithMembers]:
    teams = cast(
        list[models.Team],
        await crud_get_teams(company_id=company_id).get_async(
            executor=db, output_type=OutputType.SQLALCHEMY
        ),
    )
    if not teams:
        return []

    team_ids = [team.team_id for team in teams]
    member_rows = cast(
        list[Any],
        await get_team_members_for_teams(team_ids=team_ids).get_async(
            executor=db, output_type=OutputType.SQLALCHEMY
        ),
    )

    members_by_team_id: dict[uuid.UUID, list[UserBasic]] = {}
    for row in member_rows or []:
        members_by_team_id.setdefault(row.team_id, []).append(
            UserBasic(user_id=row.user_id, name_long=(row.name_long or ""))
        )

    return [
        TeamWithMembers(
            team_id=team.team_id,
            company_id=team.company_id,
            name_long=team.name_long,
            created_at=team.created_at,
            updated_at=team.updated_at,
            members=members_by_team_id.get(team.team_id, []),
        )
        for team in teams
    ]


@router.get(
    "",
    response_model=list[TeamInterface],
    operation_id="get_teams",
    dependencies=[Depends(dependencies.requires_admin_async)],
)
async def get_teams_route(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    company_id: uuid.UUID = Query(...),
):
    """Get teams for a company (admin only).

    Args:
        db: Database session.
        company_id: Company identifier to filter teams.
    """
    return await crud_get_teams(company_id=company_id).get_async(
        executor=db, output_type=OutputType.SQLALCHEMY
    )


@router.get(
    "/company",
    response_model=list[TeamInterface],
)
async def get_company_teams(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[UserAuthed, Depends(get_user)],
):
    """Get teams for the current user's company. No admin required.

    Args:
        db: Database session.
        user_data: Authenticated user context.
    """
    return await crud_get_teams(company_id=user_data.company_id).get_async(
        executor=db, output_type=OutputType.SQLALCHEMY
    )


@router.get(
    "/company/members",
    response_model=list[TeamWithMembers],
)
async def get_company_teams_with_members(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[UserAuthed, Depends(get_user)],
):
    """Get teams with members for the current user's company. No admin required.

    Args:
        db: Database session.
        user_data: Authenticated user context.
    """
    return await _build_teams_with_members(db=db, company_id=user_data.company_id)


@router.post(
    "",
    response_model=TeamInterface,
    status_code=201,
    operation_id="create_team",
    dependencies=[Depends(dependencies.requires_admin_async)],
)
async def create_team_route(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[UserAuthed, Depends(get_user)],
    team: TeamCreate,
):
    """Create a team for the current user's company (admin only).

    Args:
        db: Database session.
        user_data: Authenticated user context.
        team: Team payload to create.
    """
    try:
        result = await crud_create_team(
            company_id=user_data.company_id,
            team=team,
        ).get_async(
            executor=db,
            output_type=OutputType.SQLALCHEMY,
        )
        await db.commit()
        return result
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Team with this name already exists for this company",
        )


@router.get(
    "/members",
    response_model=list[TeamWithMembers],
    dependencies=[Depends(dependencies.requires_admin_async)],
)
async def get_teams_with_members_route(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    company_id: uuid.UUID = Query(...),
):
    """Get teams and members for a company (admin only).

    Args:
        db: Database session.
        company_id: Company identifier to filter teams.
    """
    return await _build_teams_with_members(db=db, company_id=company_id)


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
    """Add a member to a team (admin only).

    Args:
        team_id: Team identifier to update.
        payload: User identifier payload.
        db: Database session.
    """
    team = await crud_get_team(team_id=team_id).get_async(
        executor=db, output_type=OutputType.SQLALCHEMY
    )
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    user = await get_admin_team_user(user_id=payload.user_id).get_async(
        executor=db, output_type=OutputType.SQLALCHEMY
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await crud_add_team_member(team_id=team_id, user_id=payload.user_id).execute_async(
        executor=db
    )
    await db.commit()
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
    """Remove a member from a team (admin only).

    Args:
        team_id: Team identifier to update.
        user_id: User identifier to remove.
        db: Database session.
    """
    await crud_remove_team_member(team_id=team_id, user_id=user_id).execute_async(
        executor=db
    )
    await db.commit()
    return


@router.delete(
    "/{team_id}",
    status_code=204,
    dependencies=[Depends(dependencies.requires_admin_async)],
)
async def delete_team_route(
    team_id: uuid.UUID, db: Annotated[AsyncSession, Depends(dependencies.get_async_db)]
):
    """Delete a team (admin only).

    Args:
        team_id: Team identifier to deleteo
        db: Database session.
    """
    await crud_delete_team_assignments(team_id=team_id).execute_async(executor=db)
    await crud_delete_team_members(team_id=team_id).execute_async(executor=db)
    await crud_delete_team(team_id=team_id).execute_async(executor=db)
    await db.commit()
    return


@router.patch(
    "/{team_id}",
    response_model=TeamInterface,
    dependencies=[Depends(dependencies.requires_admin_async)],
)
async def update_team(
    team_id: uuid.UUID,
    payload: TeamUpdate,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
):
    """Update a team's name (admin only).

    Args:
        team_id: Team identifier to update.
        payload: Team update payload.
        db: Database session.
    """
    try:
        team = await crud_rename_team(team_id=team_id, payload=payload).get_async(
            executor=db, output_type=OutputType.SQLALCHEMY
        )
        if team is None:
            await db.rollback()
            raise HTTPException(status_code=404, detail="Team not found")
        await db.commit()
        return team
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Team with this name already exists for this company",
        )
