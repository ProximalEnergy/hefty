from sqlalchemy.orm import Query, Session

from core import models
from core.enumerations import UserTypeEnum
from core.model_list import ModelItem


def get_user_type(
    db: Session,
    *,
    user_type_id: UserTypeEnum,
    return_query: bool = False,
) -> ModelItem[models.UserType]:
    query: Query[models.UserType] = db.query(models.UserType).filter(
        models.UserType.user_type_id == user_type_id
    )

    return ModelItem(query=query, return_query=return_query)
