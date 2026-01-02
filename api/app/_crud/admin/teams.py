import uuid
from typing import cast

from sqlalchemy import Select, delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.interfaces import TeamCreate, TeamUpdate, TeamWithMembers, UserBasic
from core import models


async def get_teams(*, db: AsyncSession, company_id: uuid.UUID):
    """todo

    Args:
        db: TODO: describe.
        company_id: TODO: describe.
    """
    query = (
        select(models.Team)
        .where(models.Team.company_id == company_id)
        .order_by(models.Team.name_long.asc())
    )
    result = await db.execute(query)
    return result.scalars().all()


async def create_team(*, db: AsyncSession, company_id: uuid.UUID, team: TeamCreate):
    """todo

    Args:
        db: TODO: describe.
        company_id: TODO: describe.
        team: TODO: describe.
    """
    db_team = models.Team(company_id=company_id, name_long=team.name_long)
    db.add(db_team)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    await db.refresh(db_team)
    return db_team


async def get_teams_with_members(
    *, db: AsyncSession, company_id: uuid.UUID
) -> list[TeamWithMembers]:
    """todo

    Args:
        db: TODO: describe.
        company_id: TODO: describe.
    """
    teams = await get_teams(db=db, company_id=company_id)
    results: list[TeamWithMembers] = []
    for t in teams:
        user_query: Select[tuple[models.User]] = (
            select(models.User)
            .join(models.TeamMember, models.TeamMember.user_id == models.User.user_id)
            .where(models.TeamMember.team_id == t.team_id)
            .order_by(models.User.name_long.asc())
        )
        result = await db.execute(user_query)
        users = result.scalars().all()
        results.append(
            TeamWithMembers(
                team_id=t.team_id,
                company_id=t.company_id,
                name_long=t.name_long,
                created_at=t.created_at,
                updated_at=t.updated_at,
                members=[
                    UserBasic(user_id=u.user_id, name_long=(u.name_long or ""))
                    for u in users
                ],
            )
        )
    return results


async def add_team_member(*, db: AsyncSession, team_id: uuid.UUID, user_id: str):
    # ensure team exists
    """todo

    Args:
        db: TODO: describe.
        team_id: TODO: describe.
        user_id: TODO: describe.
    """
    query = select(models.Team).where(models.Team.team_id == team_id)
    result = await db.execute(query)
    team = result.scalars().first()
    if not team:
        raise ValueError("Team not found")
    # ensure user exists
    user_query = select(models.User).where(models.User.user_id == user_id)
    result = await db.execute(user_query)
    user = result.scalars().first()
    if not user:
        raise ValueError("User not found")
    # upsert behavior guarded by PK (team_id, user_id)
    db_tm = models.TeamMember(team_id=team_id, user_id=user_id)
    db.add(db_tm)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # already exists, ignore (idempotent)
    return db_tm


async def remove_team_member(*, db: AsyncSession, team_id: uuid.UUID, user_id: str):
    """todo

    Args:
        db: TODO: describe.
        team_id: TODO: describe.
        user_id: TODO: describe.
    """
    query = delete(models.TeamMember).filter(
        models.TeamMember.team_id == team_id, models.TeamMember.user_id == user_id
    )
    await db.execute(query)
    await db.commit()


async def delete_team(*, db: AsyncSession, team_id: uuid.UUID) -> dict[str, int]:
    """Delete a team and clean up dependent rows that reference it.

        Order matters due to FK constraints:
        1) operational.calendar_item_assignments (FK to admin.teams.team_id)
        2) admin.team_members (FK to admin.teams.team_id)
        3) admin.teams

    Args:
        db: TODO: describe.
        team_id: TODO: describe.
    """
    # 1) Remove calendar assignments referencing this team (operational schema)
    deleted_assignments = 0
    assignment_model = getattr(models, "CalendarItemAssignment", None)
    if assignment_model is not None:
        query = delete(assignment_model).filter(assignment_model.team_id == team_id)
        result = await db.execute(query)
        result = cast(CursorResult, result)
        deleted_assignments = result.rowcount

    # 2) Remove team member links
    query = delete(models.TeamMember).filter(models.TeamMember.team_id == team_id)
    result = await db.execute(query)
    result = cast(CursorResult, result)
    deleted_members = result.rowcount

    # 3) Remove the team itself
    query = delete(models.Team).filter(models.Team.team_id == team_id)
    result = await db.execute(query)
    result = cast(CursorResult, result)
    deleted_teams = result.rowcount

    await db.commit()
    return {
        "deleted_assignments": int(deleted_assignments),
        "deleted_members": int(deleted_members),
        "deleted_teams": int(deleted_teams),
    }


async def rename_team(*, db: AsyncSession, team_id: uuid.UUID, payload: TeamUpdate):
    """todo

    Args:
        db: TODO: describe.
        team_id: TODO: describe.
        payload: TODO: describe.
    """
    query = select(models.Team).where(models.Team.team_id == team_id)
    result = await db.execute(query)
    team = result.scalars().first()
    if not team:
        raise ValueError("Team not found")
    team.name_long = payload.name_long
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    await db.refresh(team)
    return team
