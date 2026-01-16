from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import joinedload, noload
from sqlalchemy.orm.strategy_options import _AbstractLoad

from core import models
from core.db_query import DbQuery


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
    deep: bool = False,
    device_model_ids: list[int] | None = None,
    device_type_ids: list[int] | None = None,
) -> DbQuery[models.DeviceModel, Literal[False]]:
    """Query device models with optional filters.

    Args:
        deep: Whether to eager-load device type data.
        device_model_ids: Optional list of device model IDs to filter by.
        device_type_ids: Optional list of device type IDs to filter by.
    """
    options = get_device_model_options(deep=deep)
    query = select(models.DeviceModel).options(options)

    if device_model_ids:
        query = query.where(models.DeviceModel.device_model_id.in_(device_model_ids))
    if device_type_ids:
        query = query.where(models.DeviceModel.device_type_id.in_(device_type_ids))

    return DbQuery(query=query)
