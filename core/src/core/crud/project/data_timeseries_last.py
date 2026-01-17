from datetime import datetime
from typing import Any, Literal

from sqlalchemy import extract, func, select
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.orm import joinedload

from core import models
from core.db_query import DbQuery
from core.enumerations import DeviceType, SensorType


def get_data_timeseries_latest_by_device_type(
    *,
    device_type_id: int,
    sensor_type_ids: list[int] | None = None,
    start: datetime | None = None,
) -> DbQuery:
    """Fetch the latest timeseries rows for a device type and sensors.

    Args:
        device_type_id: Device type id used to infer default sensors.
        sensor_type_ids: Optional sensor type ids to filter by.
        start: Optional start time to filter by.
    """
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

    stmt = select(
        models.DataTimeseriesLast.value_integer,
        models.DataTimeseriesLast.value_bigint,
        models.DataTimeseriesLast.value_real,
        models.DataTimeseriesLast.value_double,
        models.DataTimeseriesLast.time,
        models.Tag.device_id,
        models.Tag.sensor_type_id,
        models.Tag.unit_scale,
    ).join(models.Tag)

    stmt = stmt.where(models.Tag.sensor_type_id.in_(sensor_type_ids))

    if start:
        stmt = stmt.where(models.DataTimeseriesLast.time >= start)

    return DbQuery(query=stmt)


def get_data_timeseries_last(
    *,
    device_type_ids: list[int] | None = None,
    sensor_type_ids: list[int] | None = None,
    tag_ids: list[int] | None = None,
    device_ids: list[int] | None = None,
    deep: bool = False,
    include_ghost_tags: bool = False,
) -> DbQuery[models.DataTimeseriesLast, Literal[False]]:
    """Query the latest timeseries values with optional filters.

    Args:
        device_type_ids: Device type ids to filter tags by.
        sensor_type_ids: Sensor type ids to filter tags by.
        tag_ids: Tag ids to filter results by.
        device_ids: Device ids to filter tags by.
        deep: Whether to eager-load tag and device relationships.
        include_ghost_tags: Include tags without sensor_type_id when True.
    """
    stmt = select(models.DataTimeseriesLast)

    if (
        device_type_ids
        or sensor_type_ids
        or device_ids
        or not include_ghost_tags
        or deep
    ):
        stmt = stmt.join(
            models.Tag, models.DataTimeseriesLast.tag_id == models.Tag.tag_id
        )

    if device_type_ids:
        stmt = stmt.join(models.Device, models.Tag.device_id == models.Device.device_id)
        stmt = stmt.where(
            models.Device.device_type_id == func.any(array(device_type_ids))
        )
    elif deep:
        stmt = stmt.join(models.Device, models.Tag.device_id == models.Device.device_id)

    if sensor_type_ids:
        stmt = stmt.where(models.Tag.sensor_type_id == func.any(array(sensor_type_ids)))

    if device_ids:
        stmt = stmt.where(models.Tag.device_id == func.any(array(device_ids)))

    if tag_ids:
        stmt = stmt.where(models.DataTimeseriesLast.tag_id == func.any(array(tag_ids)))

    if not include_ghost_tags:
        stmt = stmt.where(models.Tag.sensor_type_id > 0)

    if deep:
        stmt = stmt.add_columns(
            models.Tag.unit_scale,
            models.Tag.unit_offset,
            models.Tag.device_id,
            models.Tag.sensor_type_id,
            models.Device.device_type_id,
            models.Device.name_long.label("device_name"),
        ).options(
            joinedload(models.DataTimeseriesLast.tag).joinedload(models.Tag.device)
        )

    return DbQuery(query=stmt)


def get_data_timeseries_last_v2(
    *,
    device_type_ids: list[int] | None = None,
    include_ghost_tags: bool = False,
) -> DbQuery[Any, Literal[False]]:
    """Fetches the latest timeseries data.

        If `load_only_columns` is provided, it builds an optimized query that joins
        tables and selects only the specified columns, returning a list of Rows.
        This is highly efficient for endpoints that need specific data fields.

        If `load_only_columns` is None, it uses an efficient subquery to filter
        tags and then fetches full `DataTimeseriesLast` ORM objects, which is
        ideal for general-purpose use.

    Args:
        device_type_ids: Device type ids to filter by.
        include_ghost_tags: Include tags without sensor_type_id when True.
    """
    # 1. Define the age calculation once to reuse it.
    age_in_seconds = extract("epoch", func.now() - models.DataTimeseriesLast.time)

    # 2. Create a CTE to calculate the median age for each sensor type.
    # This subquery groups the relevant data and finds the median.
    median_cte_query = (
        select(
            models.Tag.sensor_type_id,
            func.percentile_cont(0.5)
            .within_group(age_in_seconds.asc())
            .label("median_age"),
        )
        # Explicitly define the FROM and JOIN clauses for the CTE
        .select_from(models.DataTimeseriesLast)
        .join(models.Tag, models.DataTimeseriesLast.tag_id == models.Tag.tag_id)
        .join(models.Device, models.Tag.device_id == models.Device.device_id)
        # Apply filters within the CTE to reduce the aggregation scope
        # MODIFICATION: Use ANY() instead of IN() to avoid parameter limit
        .where(models.Device.device_type_id == func.any(array(device_type_ids or [])))
        .group_by(models.Tag.sensor_type_id)
    )

    # Add ghost tags filter if needed
    if not include_ghost_tags:
        median_cte_query = median_cte_query.where(models.Tag.sensor_type_id > 0)

    median_cte = median_cte_query.cte("median_ages")

    # 3. Define the columns for the main query, including from the CTE.
    columns_to_load = [
        models.DataTimeseriesLast.tag_id,
        models.DataTimeseriesLast.time,
        models.Tag.sensor_type_id,
        models.Tag.device_id,
        models.Device.device_type_id,
        models.Device.name_long.label("device_name"),
        age_in_seconds.label("age"),
        median_cte.c.median_age,  # Select the pre-calculated median
    ]

    # 4. Construct the main query, joining the detailed data with our CTE.
    stmt = (
        select(*columns_to_load)
        .select_from(models.DataTimeseriesLast)
        .join(models.Tag, models.DataTimeseriesLast.tag_id == models.Tag.tag_id)
        .join(models.Device, models.Tag.device_id == models.Device.device_id)
        .join(
            median_cte,
            median_cte.c.sensor_type_id == models.Tag.sensor_type_id,
        )
        .where(models.Device.device_type_id == func.any(array(device_type_ids or [])))
    )

    if not include_ghost_tags:
        stmt = stmt.where(models.Tag.sensor_type_id > 0)

    return DbQuery(query=stmt, use_scalars=False)
