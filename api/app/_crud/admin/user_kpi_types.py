from typing import Literal

from core.db_query import DbQuery
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core import models


def update_user_kpi_type_favorite(
    *,
    user_id: str,
    kpi_type_id: int,
    is_favorited: bool,
) -> DbQuery[models.UserKPITypes, Literal[True]]:
    """Return query updating a user's KPI type favorite state.

    If the relationship does not exist, it will be created.

    Args:
        user_id: User identifier to update.
        kpi_type_id: KPI type identifier to update.
        is_favorited: New favorite state.
    """
    query = (
        pg_insert(models.UserKPITypes)
        .values(
            user_id=user_id,
            kpi_type_id=kpi_type_id,
            is_favorited=is_favorited,
        )
        .on_conflict_do_update(
            index_elements=[
                models.UserKPITypes.user_id,
                models.UserKPITypes.kpi_type_id,
            ],
            set_={"is_favorited": is_favorited},
        )
        .returning(models.UserKPITypes)
    )
    return DbQuery(query=query, is_scalar=True)


def get_user_favorited_kpi_types(
    *,
    user_id: str,
) -> DbQuery[models.UserKPITypes, Literal[False]]:
    """Return query for all favorited KPI types for a given user.

    Args:
        user_id: The user ID to get favorited KPI types for.
    """
    query = select(models.UserKPITypes).where(
        models.UserKPITypes.user_id == user_id,
        models.UserKPITypes.is_favorited,
    )
    return DbQuery(query=query)
