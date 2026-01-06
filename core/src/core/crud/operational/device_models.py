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
    device_model_ids: list[int] | None = None,
    device_type_ids: list[int] | None = None,
    return_query: bool = False,
) -> ModelList[models.DeviceModel]:
    """TODO: add description.

    Args:
        db: TODO: describe.
        deep: TODO: describe.
        device_model_ids: Optional list of device model IDs to filter by.
        device_type_ids: Optional list of device type IDs to filter by.
        return_query: TODO: describe.
    """
    options = get_device_model_options(deep=deep)
    query = db.query(models.DeviceModel).options(options)

    if device_model_ids is not None:
        query = query.filter(models.DeviceModel.device_model_id.in_(device_model_ids))
    if device_type_ids is not None:
        query = query.filter(models.DeviceModel.device_type_id.in_(device_type_ids))

    return ModelList(query=query, return_query=return_query)
