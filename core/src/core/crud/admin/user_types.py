from typing import Literal

from sqlalchemy import select

from core import models
from core.db_query import DbQuery
from core.enumerations import UserTypeEnum


def get_user_type(
    *,
    user_type_id: UserTypeEnum,
) -> DbQuery[models.UserType, Literal[True]]:
    """TODO: add description.

    Args:
        user_type_id: TODO: describe.
    """
    query = select(models.UserType).where(models.UserType.user_type_id == user_type_id)
    return DbQuery(query=query, is_scalar=True)
