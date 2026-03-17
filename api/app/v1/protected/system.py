import datetime
from collections import defaultdict
from typing import Any

import pandas as pd
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.db_query import OutputType
from core.enumerations import SensorType, TimeOffset
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import core
from app import dependencies, utils
from app.v1.operational.project.project_data import get_project_dataframe
from core import models

router = APIRouter(
    prefix="/system/{project_id}",
    tags=["system"],
    include_in_schema=utils.get_include_in_schema(),
    dependencies=[Depends(dependencies.check_project_access_async)],
)


@router.get("/meter-power-and-expected-power-v2")
async def get_meter_power_and_expected_power_v2(
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    project: models.Project = Depends(dependencies.get_project_api),
    project_db: Session = Depends(dependencies.get_project_db),
    include_storage: bool = False,
    include_setpoint: bool = False,
    include_soiling: bool = True,
    include_degradation: bool = False,
    interval: str = "5min",
):
    """Return meter and expected power traces for a project.

    Args:
        start: Optional start datetime for the time window (project timezone).
        end: Optional end datetime for the time window (project timezone).
        project: Project model provided by dependency injection.
        project_db: Project database session used for time-series queries.
        include_storage: Whether to include PV/BESS circuit power in results.
        include_setpoint: Whether to include PPC active power setpoint values.
        include_soiling: Whether to request expected power adjusted for soiling.
        include_degradation: Whether to include degradation-adjusted expectation.
        interval: Resampling interval used for tag retrieval (e.g., "5min").
    """
    if include_soiling:
        if include_degradation:
            expected_metric_ids = [6]
        else:
            expected_metric_ids = [12]
    else:
        if include_degradation:
            expected_metric_ids = [5]
        else:
            expected_metric_ids = [11]
    # If start and end are not provided, get today's data
    if not start:
        start = pd.Timestamp.now(tz=project.time_zone).floor("5min") - pd.DateOffset(
            days=1,
        )
    elif start.tzinfo is None:
        start = pd.Timestamp(start).tz_localize(
            project.time_zone,
        )
    else:
        start = pd.Timestamp(start).tz_convert(project.time_zone)
    if not end:
        end = pd.Timestamp.now(tz=project.time_zone).floor("5min")
    elif end.tzinfo is None:
        end = pd.Timestamp(end).tz_localize(
            project.time_zone,
        )
    else:
        end = pd.Timestamp(end).tz_convert(project.time_zone)

    start = pd.Timestamp(start.replace(second=0, microsecond=0))
    end = pd.Timestamp(end.replace(second=0, microsecond=0))

    # # Determine resolution based on time range
    # duration = end - start
    # if duration < pd.Timedelta(hours=4):
    #     interval = "1min"  # 1 minute
    # else:
    #     interval = "5min"  # 5 minutes

    # Get expected power (usually 5-min interval)
    project_schema = utils.get_project_schema(project_db=project_db)
    df_expected_power = await core.crud.project.data_expected.get_project_data_expected(
        start=start,
        end=end,
        device_ids=[1],
        expected_metric_ids=expected_metric_ids,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    if not df_expected_power.empty:
        df_expected_power["time"] = pd.to_datetime(
            df_expected_power["time"], errors="coerce"
        )
        if getattr(df_expected_power["time"].dt, "tz", None) is None:
            df_expected_power["time"] = df_expected_power["time"].dt.tz_localize(
                "UTC", nonexistent="NaT", ambiguous="NaT"
            )
        df_expected_power["time"] = df_expected_power["time"].dt.tz_convert(
            project.time_zone
        )
        df_expected_power = df_expected_power.set_index("time")

        df_expected_power = pd.DataFrame(df_expected_power["value"])
        df_expected_power["value"] = (
            df_expected_power["value"] / 1_000_000
        )  # Convert from W to MW
        df_expected_power.columns = pd.Index(["Expected Power"])

        # Ensure a full date range is returned from endpoint
        # NOTE: EEM data is available at 5-minute intervals but start and end
        # might not be aligned with 5-minute interval
        full_index = pd.date_range(
            start=start.ceil("5min"),
            end=end.ceil("5min"),
            freq="5min",
            inclusive="left",
            tz=project.time_zone,
        )
        df_expected_power = df_expected_power.reindex(full_index)

    # Dynamically build sensor_type_name_shorts
    sensor_type_ids = [SensorType.METER_ACTIVE_POWER]
    if include_storage:
        sensor_type_ids.extend(
            [
                SensorType.PV_MV_COLLECTOR_CIRCUIT_METER_ACTIVE_POWER,
                SensorType.BESS_MV_CIRCUIT_METER_ACTIVE_POWER,
            ],
        )
    if include_setpoint:
        sensor_type_ids.append(SensorType.PPC_ACTIVE_POWER_SETPOINT)

    df_tags = await get_project_dataframe(
        tag_ids=[],
        sensor_type_ids=sensor_type_ids,
        sensor_type_name_shorts=[],
        start=start,
        end=end,
        project_db=project_db,
        project=project,
        get_last=True,
        last_offset="15hour",
        interval=interval,
    )

    df_meter = df_tags.xs("meter_active_power", axis=1, level=1)
    df_meter.columns = pd.Index(["Meter Active Power"])
    df_list = [df_meter]

    # Process Setpoint if included
    if (
        include_setpoint
        and "ppc_active_power_setpoint" in df_tags.columns.get_level_values(1)
    ):
        df_setpoint = df_tags.xs("ppc_active_power_setpoint", axis=1, level=1)
        # Assuming setpoint is already in MW, adjust if needed
        # If there can be multiple setpoint tags, decide how to aggregate (e.g., mean)
        # For now, assuming one or taking the first if multiple
        if isinstance(df_setpoint, pd.DataFrame):
            # If multiple tags, take the mean for simplicity, adjust if needed
            df_setpoint = pd.DataFrame(df_setpoint.mean(axis=1))
        else:
            df_setpoint = pd.DataFrame(df_setpoint)
        df_setpoint.columns = pd.Index(["PPC Active Power Setpoint"])
        df_list.append(df_setpoint)

    # Process Storage if included
    if include_storage:
        if "pv_mv_circuit_meter_active_power" in df_tags.columns.get_level_values(1):
            pv_circuit_data = df_tags.xs(
                "pv_mv_circuit_meter_active_power",
                axis=1,
                level=1,
            )
            df_pv_circuit = pd.DataFrame(pv_circuit_data.sum(axis=1))
            df_pv_circuit.columns = pd.Index(["PV Active Power"])
            df_list.append(df_pv_circuit)

        if "bess_mv_circuit_meter_active_power" in df_tags.columns.get_level_values(1):
            bess_circuit_data = df_tags.xs(
                "bess_mv_circuit_meter_active_power",
                axis=1,
                level=1,
            )
            df_bess_circuit = pd.DataFrame(bess_circuit_data.sum(axis=1))
            df_bess_circuit.columns = pd.Index(["BESS Active Power"])
            df_list.append(df_bess_circuit)

    # Concatenate all relevant dataframes
    df = pd.concat(df_list, axis=1)
    df = df.where(pd.notna(df), None)

    tags_met_station = await core.crud.project.tags.get_project_tags_v2(
        sensor_type_name_shorts=[
            "met_station_poa",
            "met_station_ambient_temperature",
            "met_station_wind_speed",
        ],
        deep=True,
    ).get_async(output_type=OutputType.POLARS, schema=project_schema)

    data_timeseries_instance = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_POLARS,
        filter_values=tags_met_station,
        query_start=start,
        query_end=end,
        project_db=project_db,
        max_lookback_period=TimeOffset.TWELVE_HOURS,
    ).get()

    df_quality = data_timeseries_instance.df
    if "time" in df_quality.columns:
        df_quality = df_quality.drop("time")

    # Create a dictionary mapping mapping sensor types name short to list of tag ids
    sensor_type_name_short_to_tag_ids = defaultdict(list)
    sensor_type_name_short_to_name_long: dict[str, str] = {}
    tag_rows = tags_met_station.select(
        ["tag_id", "sensor_type_name_short", "sensor_type_name_long"]
    ).iter_rows(named=True)
    for row in tag_rows:
        name_short = row["sensor_type_name_short"]
        if not name_short:
            continue
        tag_id = row["tag_id"]
        sensor_type_name_short_to_tag_ids[name_short].append(tag_id)
        if name_short not in sensor_type_name_short_to_name_long:
            name_long = row["sensor_type_name_long"] or name_short
            sensor_type_name_short_to_name_long[name_short] = name_long

    quality_raw = {}

    for sensor_type_name_short, tag_ids in sensor_type_name_short_to_tag_ids.items():
        quality_raw[sensor_type_name_short] = 0
        for tag_id in tag_ids:
            if tag_id not in df_quality.columns:
                continue
            series = df_quality[tag_id]
            series_sum = series.sum()
            has_nulls = series.null_count() > 0
            is_zero = series_sum is None or series_sum == 0
            if not (is_zero or has_nulls):
                quality_raw[sensor_type_name_short] += 1

    quality: dict[str, Any] = {}
    quality["details"] = []
    for sensor_type_name_short in quality_raw:
        name_long = sensor_type_name_short_to_name_long[sensor_type_name_short]
        total = len(sensor_type_name_short_to_tag_ids[sensor_type_name_short])
        count = quality_raw[sensor_type_name_short]
        percent = count / total
        level = "good" if percent == 1 else "warning" if percent > 0.5 else "bad"

        message = (
            f"All {name_long} sensors nominal"
            if count == total
            else (f"{total - count}/{total} {name_long} sensors are not reporting")
        )

        quality["details"].append({"level": level, "message": message})

    # Find the "lowest" level level. "good" > "warning" > "bad"
    quality["level"] = "good"
    for detail in quality["details"]:
        if detail["level"] == "warning" and quality["level"] == "good":
            quality["level"] = "warning"
        if detail["level"] == "bad":
            quality["level"] = "bad"

    quality["message"] = "Data quality evaluated over the plotted interval"

    data = [
        {
            "x": df.index.tz_convert(project.time_zone).tolist(),
            "y": df[col].tolist(),
            "name": col,
        }
        for col in df.columns
    ]

    data.extend(
        {
            "x": df_expected_power.index.tolist(),
            "y": df_expected_power[col].tolist(),
            "name": col,
        }
        for col in df_expected_power.columns
    )

    return {
        "data": data,
        "quality": quality,
    }
