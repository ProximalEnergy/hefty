from typing import Literal

from core.db_query import DbQuery
from sqlalchemy import select

from core import models


def get_permissions(
    *,
    permission_ids: list[int] | None = None,
) -> DbQuery[models.Permission, Literal[False]]:
    """Query the permissions table

    Args:
        permission_ids: A list of permission IDs to filter the query. If not
            provided, all permissions are returned.
    """
    query = select(models.Permission)
    # Cannot be `if permission_ids` because permission_ids can be an empty list
    # which is falsy
    if permission_ids is not None:
        query = query.where(models.Permission.permission_id.in_(permission_ids))
    return DbQuery(query=query)
