from sqlalchemy.orm import Session, noload, selectinload
from sqlalchemy.orm.strategy_options import _AbstractLoad

from core import models
from core.model_list import ModelList


def get_device_model_options(*, deep: bool) -> _AbstractLoad:
    """TODO: add description.

    Args:
        deep: TODO: describe.
    """
    if deep:
        options = selectinload(models.DeviceModel.device_type)
    else:
        options = noload(models.DeviceModel.device_type)

    return options


def get_device_models(
    *,
    db: Session,
    deep: bool = False,
    return_query: bool = False,
) -> ModelList[models.DeviceModel]:
    """TODO: add description.

    Args:
        db: TODO: describe.
        deep: TODO: describe.
        return_query: TODO: describe.
    """
    options = get_device_model_options(deep=deep)
    query = db.query(models.DeviceModel).options(options)

    return ModelList(query=query, return_query=return_query)
