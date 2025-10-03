from sqlalchemy.orm import Session

from core import models
from core.model_list import ModelItem, ModelList


def get_sensor_type(
    *, db: Session, sensor_type_id: int, return_query: bool = False
) -> ModelItem[models.SensorType]:
    query = db.query(models.SensorType).filter(
        models.SensorType.sensor_type_id == sensor_type_id
    )
    return ModelItem(query=query, return_query=return_query)


def get_sensor_types(
    db: Session,
    *,
    sensor_type_ids: list[int] | None = [],
    name_short: str = "",
    name_long: str = "",
    name_metric: str = "",
    unit: str = "",
    return_query: bool = False,
) -> ModelList[models.SensorType]:
    query = db.query(models.SensorType)

    if sensor_type_ids:
        query = query.filter(models.SensorType.sensor_type_id.in_(sensor_type_ids))
    if name_short:
        query = query.filter(models.SensorType.name_short == name_short)
    if name_long:
        query = query.filter(models.SensorType.name_long == name_long)
    if name_metric:
        query = query.filter(models.SensorType.name_metric == name_metric)
    if unit:
        query = query.filter(models.SensorType.unit == unit)

    return ModelList(query=query, return_query=return_query)
