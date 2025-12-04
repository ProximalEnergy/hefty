from uuid import UUID

from sqlalchemy import extract, func, select  # Make sure to import 'select'
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.orm import Session, selectinload

from core import models
from core.enumerations import DeviceType, SensorType
from core.model_list import ModelList


def get_data_timeseries_latest_by_device_type(
    db: Session,
    *,
    project_id: UUID,
    device_type_id: int,
    sensor_type_ids: list[int] | None = None,
    return_query: bool = False,
) -> ModelList[models.DataTimeseriesLast]:
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
    return ModelList(query=query, return_query=return_query)


def get_data_timeseries_last(
    project_db: Session,
    *,
    device_type_ids: list[int] | None = None,
    sensor_type_ids: list[int] | None = None,
    tag_ids: list[int] | None = None,
    device_ids: list[int] | None = None,
    deep: bool = False,
    return_query: bool = False,
    include_ghost_tags: bool = False,
) -> ModelList[models.DataTimeseriesLast]:
    query = project_db.query(models.DataTimeseriesLast)
    tag_sets: list[set[int]] = []
    if sensor_type_ids:
        tags = project_db.query(models.Tag).filter(
            models.Tag.sensor_type_id.in_(sensor_type_ids)
        )
        tag_items = tags.all()
        tag_ids_filtered = {tag.tag_id for tag in tag_items}
        tag_sets.append(tag_ids_filtered)

    if device_type_ids:
        Device = models.Device
        tags = (
            project_db.query(models.Tag)
            .join(Device, models.Tag.device)  # Explicit join via relationship
            .filter(Device.device_type_id.in_(device_type_ids))
        )
        tag_items = tags.all()
        tag_ids_filtered = {tag.tag_id for tag in tag_items}
        tag_sets.append(tag_ids_filtered)

    if device_ids:
        tags = project_db.query(models.Tag).filter(models.Tag.device_id.in_(device_ids))
        tag_items = tags.all()
        tag_ids_filtered = {tag.tag_id for tag in tag_items}
        tag_sets.append(tag_ids_filtered)

    if tag_ids:
        tag_sets.append(set(tag_ids))

    if tag_sets:
        final_tag_ids: list[int] = list(set.intersection(*tag_sets))
        query = query.filter(models.DataTimeseriesLast.tag_id.in_(final_tag_ids))

    if not include_ghost_tags:
        # Join with Tag table to filter out tags with no sensor_type_id (i.e., ghost tags)
        subq = (
            project_db.query(models.Tag.tag_id)
            .filter(models.Tag.sensor_type_id > 0)
            .subquery()
        )
        query = query.filter(models.DataTimeseriesLast.tag_id.in_(select(subq)))

    if deep:
        query = query.options(
            selectinload(models.DataTimeseriesLast.tag).selectinload(models.Tag.device)
        )

    return ModelList(query=query, return_query=return_query)


def get_data_timeseries_last_v2(
    *,
    project_db: Session,
    device_type_ids: list[int] | None = None,
    sensor_type_ids: list[int] | None = None,
    tag_ids: list[int] | None = None,
    device_ids: list[int] | None = None,
    deep: bool = False,
    return_query: bool = True,
    include_ghost_tags: bool = False,
) -> ModelList[models.DataTimeseriesLast]:
    """
    Fetches the latest timeseries data.

    If `load_only_columns` is provided, it builds an optimized query that joins
    tables and selects only the specified columns, returning a list of Rows.
    This is highly efficient for endpoints that need specific data fields.

    If `load_only_columns` is None, it uses an efficient subquery to filter
    tags and then fetches full `DataTimeseriesLast` ORM objects, which is
    ideal for general-purpose use.
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
    query = (
        project_db.query(*columns_to_load)
        .join(models.DataTimeseriesLast.tag)
        .join(models.Tag.device)
        .join(
            median_cte,
            median_cte.c.sensor_type_id == models.Tag.sensor_type_id,
        )
        # MODIFICATION: Use ANY() instead of IN() here as well
        .where(models.Device.device_type_id == func.any(array(device_type_ids or [])))
    )

    # 4. Construct the main query, joining the detailed data with our CTE.
    query = (
        project_db.query(*columns_to_load)
        .join(models.DataTimeseriesLast.tag)
        .join(models.Tag.device)
        .join(
            median_cte,
            median_cte.c.sensor_type_id == models.Tag.sensor_type_id,
        )
        # MODIFICATION: Use ANY() instead of IN() here as well
        .where(models.Device.device_type_id == func.any(array(device_type_ids or [])))
    )

    if not include_ghost_tags:
        query = query.where(models.Tag.sensor_type_id > 0)

    return ModelList(query=query, return_query=return_query)
