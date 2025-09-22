import datetime

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
            2: [2, 9],  # pv_pcs: [pv_pcs_ac_power, pv_pcs_ac_power_setpoint]
            9: [27],  # pv_dc_combiner: [pv_dc_combiner_current]
            29: [24, 25],  # tracker_row: [tracker_position, tracker_setpoint]
        }
        sensor_type_ids = device_type_id_to_sensor_type_ids.get(device_type_id, [])

    query = db.query(models.DataTimeseriesLast).options(
        selectinload(models.DataTimeseriesLast.tag),
    )
    query = query.join(models.Tag).where(models.Tag.sensor_type_id.in_(sensor_type_ids))
    if start:
        query = query.filter(models.DataTimeseriesLast.time >= start)
    return query.all()
