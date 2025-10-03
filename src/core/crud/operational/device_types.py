from sqlalchemy.orm import Session

from core import models
from core.model_list import ModelItem, ModelList


def get_device_type(
    db: Session, *, device_type_id: int, return_query: bool = False
) -> ModelItem[models.DeviceType]:
    query = db.query(models.DeviceType).filter(
        models.DeviceType.device_type_id == device_type_id
    )
    return ModelItem(query=query, return_query=return_query)


def get_device_types(
    db: Session,
    *,
    device_type_ids: list[int] = [],
    name_short: str = "",
    name_long: str = "",
    only_included_by_default: bool = True,
    return_query: bool = False,
) -> ModelList[models.DeviceType]:
    """
    Retrieve a list of device types from the database based on the provided filters.

    Args:
        db (Session): The database session to use for the query.
        device_type_ids (list[int], optional): A list of device type IDs to filter the results. Defaults to an empty list.
        name_short (str, optional): A short name to filter the device types. Defaults to an empty string.
        name_long (str, optional): A long name to filter the device types. Defaults to an empty string.
        only_included_by_default (bool, optional): A flag to filter device types based on their default inclusion status. Defaults to True.

    Returns:
        list[models.DeviceType]: A list of device types matching the specified criteria.
    """
    query = db.query(models.DeviceType)

    if device_type_ids:
        query = query.filter(models.DeviceType.device_type_id.in_(device_type_ids))
    if name_short:
        query = query.filter(models.DeviceType.name_short == name_short)
    if name_long:
        query = query.filter(models.DeviceType.name_long == name_long)
    if only_included_by_default:
        query = query.filter(models.DeviceType.include_by_default.is_(True))

    return ModelList(query=query, return_query=return_query)
