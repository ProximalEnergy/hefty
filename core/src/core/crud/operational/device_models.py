from sqlalchemy.orm import Session, joinedload, noload
from sqlalchemy.orm.strategy_options import _AbstractLoad

from core import models
from core.model_list import ModelList


def get_device_model_options(*, deep: bool) -> _AbstractLoad:
    """Return loader options for device model queries.

    Args:
        deep: Whether to eager-load device type data.
    """
    if deep:
        options = joinedload(models.DeviceModel.device_type)
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
    """Query device models with optional filters.

    Args:
        db: Operational database session.
        deep: Whether to eager-load device type data.
        device_model_ids: Optional list of device model IDs to filter by.
        device_type_ids: Optional list of device type IDs to filter by.
        return_query: Return the query without executing when True.
    """
    options = get_device_model_options(deep=deep)
    query = db.query(models.DeviceModel).options(options)

    if device_model_ids is not None:
        query = query.where(models.DeviceModel.device_model_id.in_(device_model_ids))
    if device_type_ids is not None:
        query = query.where(models.DeviceModel.device_type_id.in_(device_type_ids))

    return ModelList(query=query, return_query=return_query)
