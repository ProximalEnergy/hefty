import datetime
from collections import defaultdict
from typing import Any

import pandas as pd
from core.dependencies import get_db
from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse
from sqlalchemy.orm import Session

import core
from app import dependencies, utils
from app.v1.operational.project.project_data import get_project_dataframe
from core import models

router = APIRouter(
    prefix="/system/{project_id}",
    tags=["system"],
    include_in_schema=utils.get_include_in_schema(),
)


@router.get("/meter-power-and-expected-power-v2", response_class=ORJSONResponse)
def get_meter_power_and_expected_power_v2(
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    project: models.Project = Depends(dependencies.get_project_api),
    db: Session = Depends(get_db),
    project_db: Session = Depends(dependencies.get_project_db),
    include_storage: bool = False,
    include_setpoint: bool = False,
    include_soiling: bool = True,
    include_degradation: bool = False,
    interval: str = "5min",
):
    """todo

    Args:
        start: TODO: describe.
        end: TODO: describe.
        project: TODO: describe.
        db: TODO: describe.
        project_db: TODO: describe.
        include_storage: TODO: describe.
        include_setpoint: TODO: describe.
        include_soiling: TODO: describe.
        include_degradation: TODO: describe.
        interval: TODO: describe.
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
    df_expected_power = core.crud.project.data_expected.get_project_data_expected(
        project_db,
        start=start,
        end=end,
        device_ids=[1],
        expected_metric_ids=expected_metric_ids,
    ).pandas_dataframe(index="time", as_datetime=True, tz=project.time_zone)

    if not df_expected_power.empty:
        df_expected_power = pd.DataFrame(df_expected_power["value"])
        df_expected_power["value"] = (
            df_expected_power["value"] / 1_000_000
        )  # Convert from W to MW
        df_expected_power.columns = pd.Index(["Expected Power"])

        # Ensure a full date range is returned from endpoint
        # NOTE: EEM data is available at 5-minute intervals but start and end might not be aligned with 5-minute interval
        full_index = pd.date_range(
            start=start.ceil("5min"),
            end=end.ceil("5min"),
            freq="5min",
            inclusive="left",
            tz=project.time_zone,
        )
        df_expected_power = df_expected_power.reindex(full_index)

    # Dynamically build sensor_type_name_shorts
    sensor_type_name_shorts = ["meter_active_power"]
    if include_storage:
        sensor_type_name_shorts.extend(
            ["pv_mv_circuit_meter_active_power", "bess_mv_circuit_meter_active_power"],
        )
    if include_setpoint:
        sensor_type_name_shorts.append("ppc_active_power_setpoint")

    df_tags = get_project_dataframe(
        tag_ids=[],
        sensor_type_name_shorts=sensor_type_name_shorts,
        start=start,
        end=end,
        db=db,
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

    tags_met_station = core.crud.project.tags.get_project_tags(
        project_db,
        sensor_type_name_shorts=[
            "met_station_poa",
            "met_station_ambient_temperature",
            "met_station_wind_speed",
        ],
        deep=True,
    ).models()

    df_quality = utils.data_df(
        project_db,
        project,
        tags_met_station,
        start=start,
        end=end,
        fillna_zero=False,
        get_last=True,
        last_offset="15hour",
    )

    # Create a dictionary mapping mapping sensor types name short to list of tag ids
    sensor_type_name_short_to_tag_ids = defaultdict(list)
    for tag in tags_met_station:
        sensor_type_name_short_to_tag_ids[tag.sensor_type.name_short].append(tag.tag_id)

    sensor_type_name_short_to_name_long = {
        tag.sensor_type.name_short: tag.sensor_type.name_long
        for tag in tags_met_station
    }

    quality_raw = {}

    for sensor_type_name_short, tag_ids in sensor_type_name_short_to_tag_ids.items():
        quality_raw[sensor_type_name_short] = 0
        for tag_id in tag_ids:
            if not (
                df_quality[tag_id].sum() == 0 or df_quality[tag_id].isna().sum() > 0
            ):
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
        if detail["level"] == "warning" and quality["level"] == "good":  # type: ignore
            quality["level"] = "warning"
        if detail["level"] == "bad":  # type: ignore
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
