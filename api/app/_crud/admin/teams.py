import uuid
from typing import Any, Literal

from core.db_query import DbQuery
from sqlalchemy import Select, delete, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.interfaces import TeamCreate, TeamUpdate
from core import models


def get_teams(*, company_id: uuid.UUID) -> DbQuery[models.Team, Literal[False]]:
    query = (
        select(models.Team)
        .where(models.Team.company_id == company_id)
        .order_by(models.Team.name_long.asc())
    )
    return DbQuery(query=query)


def create_team(
    *, company_id: uuid.UUID, team: TeamCreate
) -> DbQuery[models.Team, Literal[True]]:
    query = (
        insert(models.Team)
        .values(company_id=company_id, name_long=team.name_long)
        .returning(models.Team)
    )
    return DbQuery(query=query, is_scalar=True)


def get_team(*, team_id: uuid.UUID) -> DbQuery[models.Team, Literal[True]]:
    query = select(models.Team).where(models.Team.team_id == team_id)
    return DbQuery(query=query, is_scalar=True)


def get_admin_team_user(*, user_id: str) -> DbQuery[models.User, Literal[True]]:
    query = select(models.User).where(models.User.user_id == user_id)
    return DbQuery(query=query, is_scalar=True)


def get_team_members(*, team_id: uuid.UUID) -> DbQuery[models.User, Literal[False]]:
    query: Select[tuple[models.User]] = (
        select(models.User)
        .join(models.TeamMember, models.TeamMember.user_id == models.User.user_id)
        .where(models.TeamMember.team_id == team_id)
        .order_by(models.User.name_long.asc())
    )
    return DbQuery(query=query)


def get_team_members_for_teams(
    *, team_ids: list[uuid.UUID]
) -> DbQuery[Any, Literal[False]]:
    query = (
        select(
            models.TeamMember.team_id,
            models.User.user_id,
            models.User.name_long,
        )
        .join(models.TeamMember, models.TeamMember.user_id == models.User.user_id)
        .where(models.TeamMember.team_id.in_(team_ids))
        .order_by(models.TeamMember.team_id.asc(), models.User.name_long.asc())
    )
    return DbQuery(query=query)


def add_team_member(
    *, team_id: uuid.UUID, user_id: str
) -> DbQuery[None, Literal[False]]:
    query = (
        pg_insert(models.TeamMember)
        .values(team_id=team_id, user_id=user_id)
        .on_conflict_do_nothing()
    )
    return DbQuery(query=query)


def remove_team_member(
    *, team_id: uuid.UUID, user_id: str
) -> DbQuery[None, Literal[False]]:
    query = delete(models.TeamMember).where(
        models.TeamMember.team_id == team_id, models.TeamMember.user_id == user_id
    )
    return DbQuery(query=query)


def delete_team_assignments(*, team_id: uuid.UUID) -> DbQuery[None, Literal[False]]:
    assignment_model = getattr(models, "CalendarItemAssignment", None)
    if assignment_model is None:
        query = delete(models.TeamMember).where(models.TeamMember.team_id == team_id)
        return DbQuery(query=query)

    query = delete(assignment_model).where(assignment_model.team_id == team_id)
    return DbQuery(query=query)


def delete_team_members(*, team_id: uuid.UUID) -> DbQuery[None, Literal[False]]:
    query = delete(models.TeamMember).where(models.TeamMember.team_id == team_id)
    return DbQuery(query=query)


def delete_team(*, team_id: uuid.UUID) -> DbQuery[None, Literal[False]]:
    query = delete(models.Team).where(models.Team.team_id == team_id)
    return DbQuery(query=query)


def rename_team(
    *, team_id: uuid.UUID, payload: TeamUpdate
) -> DbQuery[models.Team, Literal[True]]:
    query = (
        update(models.Team)
        .where(models.Team.team_id == team_id)
        .values(name_long=payload.name_long)
        .returning(models.Team)
    )
    return DbQuery(query=query, is_scalar=True)
