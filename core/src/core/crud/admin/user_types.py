from sqlalchemy import select

from core import models
from core.enumerations import UserTypeEnum
from core.model_list import ModelList


def get_user_type(
    *,
    user_type_id: UserTypeEnum,
    return_query: bool = True,
) -> ModelList[models.UserType]:
    """TODO: add description.

    Args:
        user_type_id: TODO: describe.
        return_query: TODO: describe.
    """
    query = select(models.UserType).filter(models.UserType.user_type_id == user_type_id)
    return ModelList(query=query, return_query=return_query)
