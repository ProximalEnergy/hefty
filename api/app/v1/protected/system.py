import datetime
from collections import defaultdict

import pandas as pd
import polars as pl
from core.crud.operational.sensor_types import get_sensor_types
from core.crud.project.data_expected import get_project_data_expected
from core.crud.project.data_timeseries import (
    DataTimeseries,
    FilterMethod,
    TimeInterval,
    TimeOffset,
)
from core.crud.project.tags import get_project_tags_v2
from core.db_query import OutputType
from core.enumerations import SensorType, TimeOffset
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import dependencies, utils
from core import models


class MeterPowerAndExpectedPowerV3Trace(BaseModel):
    """Meter and expected power traces for a project."""

    x: list[datetime.datetime]
    y: list[float | None]
    sensor_type_id: int
    name: str


router = APIRouter(
    prefix="/system/{project_id}",
    tags=["system"],
    include_in_schema=utils.get_include_in_schema(),
    dependencies=[Depends(dependencies.check_project_access_async)],
)


@router.get("/meter-power-and-expected-power-v3")
async def get_meter_power_and_expected_power_v3(
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    project: models.Project = Depends(dependencies.get_project_api),
    project_db: Session = Depends(dependencies.get_project_db),
    include_storage: bool = False,
    include_setpoint: bool = False,
    include_soiling: bool = True,
    include_degradation: bool = False,
    interval: str = "5min",
) -> list[MeterPowerAndExpectedPowerV3Trace]:
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

    df_expected_power = await get_project_data_expected(
        start=start,
        end=end,
        expected_metric_ids=expected_metric_ids,
    ).get_async(output_type=OutputType.PANDAS, schema=project.name_short)
    exp_data: MeterPowerAndExpectedPowerV3Trace | None = None
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
    sensor_type_ids = [SensorType.METER_ACTIVE_POWER, SensorType.PV_EXPECTED_POWER]
    if include_storage:
        sensor_type_ids.extend(
            [
                SensorType.PV_MV_COLLECTOR_CIRCUIT_METER_ACTIVE_POWER,
                SensorType.BESS_MV_CIRCUIT_METER_ACTIVE_POWER,
            ],
        )
    if include_setpoint:
        sensor_type_ids.append(SensorType.PPC_ACTIVE_POWER_SETPOINT)

    tags_pl = await get_project_tags_v2(
        sensor_type_ids=sensor_type_ids,
    ).get_async(output_type=OutputType.POLARS, schema=project.name_short)
    sensor_types_pl = await get_sensor_types(
        sensor_type_ids=[s.value for s in sensor_type_ids]
    ).get_async(output_type=OutputType.POLARS, schema=project.name_short)

    try:
        freq = TimeInterval(interval)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid interval")

    data_timeseries = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_POLARS,
        filter_values=tags_pl,
        query_start=start,
        query_end=end,
        project_db=project_db,
        freq=freq,
        max_lookback_period=TimeOffset.TWELVE_HOURS,
    ).get()

    df = data_timeseries.df
    if df.is_empty():
        return []

    time_col = "time" if "time" in df.columns else "time_bucket"
    x_values = df[time_col].to_list()

    sensor_type_id_to_tag_cols: dict[int, list[str]] = defaultdict(list)
    for row in tags_pl.select(["tag_id", "sensor_type_id"]).iter_rows(named=True):
        sensor_type_id = row["sensor_type_id"]
        if sensor_type_id is None:
            continue
        sensor_type_id_to_tag_cols[int(sensor_type_id)].append(str(row["tag_id"]))

    sensor_type_id_to_name_long: dict[int, str] = {}
    for row in sensor_types_pl.select(
        ["sensor_type_id", "name_long", "name_short"]
    ).iter_rows(named=True):
        sensor_type_id = int(row["sensor_type_id"])
        sensor_type_id_to_name_long[sensor_type_id] = (
            row["name_long"] or row["name_short"] or str(sensor_type_id)
        )

    selected_sensor_type_ids = [int(s) for s in sensor_type_ids]

    # Build one derived column per sensor type.
    y_alias_by_sensor_type_id: dict[int, str] = {}
    y_exprs: list[pl.Expr] = []
    for sensor_type_id in selected_sensor_type_ids:
        tag_cols = sensor_type_id_to_tag_cols.get(sensor_type_id, [])
        existing_tag_cols = [c for c in tag_cols if c in df.columns]
        if not existing_tag_cols:
            continue

        y_alias = f"st_{sensor_type_id}"
        y_alias_by_sensor_type_id[sensor_type_id] = y_alias

        sum_expr = pl.sum_horizontal(
            [pl.col(c).fill_null(0.0) for c in existing_tag_cols]
        ).cast(pl.Float64)

        non_null_count_expr = pl.sum_horizontal(
            [pl.col(c).is_not_null().cast(pl.Int32) for c in existing_tag_cols]
        )

        y_expr = (
            pl.when(non_null_count_expr == 0)
            .then(pl.lit(None, dtype=pl.Float64))
            .otherwise(sum_expr)
            .alias(y_alias)
        )
        y_exprs.append(y_expr)

    wide = df.select([pl.col(time_col), *y_exprs])

    data: list[MeterPowerAndExpectedPowerV3Trace] = []
    for sensor_type_id in selected_sensor_type_ids:
        y_alias = y_alias_by_sensor_type_id.get(sensor_type_id) or ""
        if not y_alias:
            continue
        data.append(
            MeterPowerAndExpectedPowerV3Trace(
                x=x_values,
                y=wide[y_alias].to_list(),
                sensor_type_id=sensor_type_id,
                name=sensor_type_id_to_name_long.get(
                    sensor_type_id, str(sensor_type_id)
                ),
            )
        )
    if not df_expected_power.empty:
        exp_data = MeterPowerAndExpectedPowerV3Trace(
            x=df_expected_power.index.tolist(),
            y=df_expected_power["value"].values.tolist(),
            sensor_type_id=SensorType.PV_EXPECTED_POWER,
            name=sensor_type_id_to_name_long[SensorType.PV_EXPECTED_POWER],
        )
        data.append(exp_data)
    return data
