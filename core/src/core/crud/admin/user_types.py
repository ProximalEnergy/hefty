from typing import Literal

from core.db_query import DbQuery
from core.enumerations import UserTypeEnum
from sqlalchemy import select

from core import models


def get_user_type(
    *,
    user_type_id: UserTypeEnum,
) -> DbQuery[models.UserType, Literal[True]]:
    """Build a query for a single user type by id.

    Args:
        user_type_id: User type enum value to fetch.
    """
    query = select(models.UserType).where(models.UserType.user_type_id == user_type_id)
    return DbQuery(query=query, is_scalar=True)
