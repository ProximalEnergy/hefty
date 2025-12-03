import datetime

from core.enumerations import DeviceType, SensorType
from sqlalchemy.orm import Session, selectinload

from core import models


def get_data_timeseries_latest_by_device_type(
    *,
    db: Session,
    device_type_id: int,
    sensor_type_ids: list[int] | None = None,
    start: datetime.datetime | None = None,
):
    if not sensor_type_ids:
        device_type_id_to_sensor_type_ids: dict[int, list[int]] = {
            DeviceType.PV_PCS.value: [
                SensorType.PV_PCS_AC_POWER.value,
                SensorType.PV_PCS_AC_POWER_SETPOINT.value,
            ],
            DeviceType.PV_DC_COMBINER.value: [
                SensorType.PV_DC_COMBINER_CURRENT.value,
            ],
            DeviceType.TRACKER_ROW.value: [
                SensorType.TRACKER_POSITION.value,
                SensorType.TRACKER_SETPOINT.value,
            ],
        }
        sensor_type_ids = device_type_id_to_sensor_type_ids.get(device_type_id, [])

    query = db.query(models.DataTimeseriesLast).options(
        selectinload(models.DataTimeseriesLast.tag),
    )
    query = query.join(models.Tag).where(models.Tag.sensor_type_id.in_(sensor_type_ids))
    if start:
        query = query.filter(models.DataTimeseriesLast.time >= start)
    return query.all()
