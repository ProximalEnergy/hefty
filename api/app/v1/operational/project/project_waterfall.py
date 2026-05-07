import datetime
from typing import Annotated

import pandas as pd
from core.crud.operational.device_types import get_device_types as crud_get_device_types
from core.crud.operational.failure_modes import get_failure_modes
from core.crud.operational.kpi_data import get_project_kpi_data_agg
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.crud.project.event_losses import get_event_losses_aggregated
from core.db_query import OutputType
from core.enumerations import (
    EventLossTypeEnum,
    KPITypeEnum,
    ProjectTypeEnum,
    SensorTypeEnum,
)
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import dependencies
from app._crud.projects import pv_budgeted as crud_pv_budgeted
from app._crud.projects.pv_expected import get_pv_expected as crud_get_pv_expected
from core import crud, models

DESCRIPTION_404 = "Tag not found"


def _waterfall_kpi_date_range_exclusive_end(
    *,
    start_dt: datetime.datetime,
    end_dt: datetime.datetime,
    time_zone: str,
) -> tuple[datetime.date, datetime.date]:
    """Map waterfall window to KPI date bounds (end exclusive).

    Args:
        start_dt: Inclusive range start (timezone-aware or UTC).
        end_dt: Inclusive range end (typically end-of-day).
        time_zone: Project IANA timezone name.

    Returns:
        Pair ``(start_date, end_exclusive_date)`` for ``get_project_kpi_data_agg``.
    """
    ts_start = pd.Timestamp(start_dt)
    ts_end = pd.Timestamp(end_dt)
    if ts_start.tz is None:
        ts_start = ts_start.tz_localize("UTC")
    if ts_end.tz is None:
        ts_end = ts_end.tz_localize("UTC")
    local_start = ts_start.tz_convert(time_zone).date()
    local_end_inclusive = ts_end.tz_convert(time_zone).date()
    end_exclusive = local_end_inclusive + datetime.timedelta(days=1)
    return local_start, end_exclusive


router = APIRouter(
    prefix="/waterfall",
    tags=["project_waterfall"],
)


def df_from_objects(
    *,
    objects: list,
    index_col: str,
    time_zone: str | None = None,
) -> pd.DataFrame:
    """todo

    Args:
        objects: Description for objects.
        index_col: Description for index_col.
        time_zone: Description for time_zone.
    """
    records = [obj.__dict__ for obj in objects]
    df = pd.DataFrame.from_records(records).set_index(index_col)
    if "_sa_instance_state" in df.columns:
        df = df.drop(columns=["_sa_instance_state"])
    if time_zone is not None:
        df.index = pd.to_datetime(df.index).tz_convert(time_zone)
    return df


@router.get("")
async def get_project_waterfall(
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    level: str = "device_type",
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
):
    """todo

    Args:
        db: Description for db.
        project_db: Description for project_db.
        project: Description for project.
        level: Description for level.
        start: Description for start.
        end: Description for end.
    """
    if start is None or end is None:
        start = pd.Timestamp.now(tz=project.time_zone).floor("D") - pd.Timedelta(days=1)
        end = pd.Timestamp.now(tz=project.time_zone).floor("D")
    # Convert Timestamps to datetime.datetime for type checking
    start_dt = start.to_pydatetime() if isinstance(start, pd.Timestamp) else start
    end_dt = end.to_pydatetime() if isinstance(end, pd.Timestamp) else end
    if start_dt is None or end_dt is None:
        raise ValueError("start and end must not be None")
    match project.project_type_id:
        case ProjectTypeEnum.PV:
            meter_tags_df = await crud.project.tags.get_project_tags_v2(
                sensor_type_ids=[SensorTypeEnum.METER_ACTIVE_POWER],
                deep=True,
            ).get_async(
                output_type=OutputType.POLARS,
                schema=project.name_short,
            )

            data_timeseries_instance = await DataTimeseries(
                project_name_short=project.name_short,
                filter_method=FilterMethod.TAG_POLARS,
                filter_values=meter_tags_df,
                query_start=start,
                query_end=end,
                project_db=project_db,
            ).get()

            df_meter = data_timeseries_instance.df.to_pandas()
            df_meter = df_meter.set_index("time")
            df_meter.index = pd.to_datetime(df_meter.index).tz_convert(
                project.time_zone
            )
            df_meter.columns = df_meter.columns.astype(int)

            series_meter = df_meter.iloc[:, 0]
            series_meter.name = "Meter Active Power"
        case ProjectTypeEnum.BESS:
            return []
        case ProjectTypeEnum.PVS:
            meter_tags_df = await crud.project.tags.get_project_tags_v2(
                sensor_type_ids=[
                    SensorTypeEnum.PV_MV_COLLECTOR_CIRCUIT_METER_ACTIVE_POWER
                ],
                deep=True,
            ).get_async(
                output_type=OutputType.POLARS,
                schema=project.name_short,
            )

            data_timeseries_instance = await DataTimeseries(
                project_name_short=project.name_short,
                filter_method=FilterMethod.TAG_POLARS,
                filter_values=meter_tags_df,
                query_start=start,
                query_end=end,
                project_db=project_db,
            ).get()

            df_meter = data_timeseries_instance.df.to_pandas()
            df_meter = df_meter.set_index("time")
            df_meter.index = pd.to_datetime(df_meter.index).tz_convert(
                project.time_zone
            )
            df_meter.columns = df_meter.columns.astype(int)

            series_meter = df_meter.sum(axis=1)
            series_meter.name = "Meter Active Power"

    ## Add a series of sequential fallbacks if preferred metric is not available
    ## TODO: integrate this into a table instead
    # POI expected metrics: prefer warranted degradation, then fall back.
    # 6 = soiling + degradation, 5 = degradation only, 12/11 = no degradation.
    expected_metric_ids = [6, 5, 12, 11]
    data_expected = []
    for metric_id in expected_metric_ids:
        data_expected = crud_get_pv_expected(
            db=project_db,
            start=start_dt,
            end=end_dt,
            expected_metric_ids=[metric_id],
        )
        if data_expected:
            break
    if len(data_expected) == 0:
        return {
            "value": [],
            "measure": [],
            "name": [],
        }
    df_expected = df_from_objects(
        objects=data_expected,
        index_col="time",
        time_zone=project.time_zone,
    )
    events_query = crud.project.events.get_windowed_event_summaries(
        start=start,
        end=end,
    )
    data_events = await events_query.get_async(
        schema=project.name_short,
        output_type=OutputType.PANDAS,
    )
    df_events = data_events.set_index("event_id")
    # Use aggregated query - much faster than fetching all individual loss records
    event_losses_dict = get_event_losses_aggregated(
        db=project_db,
        time_gte=start,
        time_lt=end,
        event_ids=df_events.index.tolist(),
        event_loss_type_id=EventLossTypeEnum.PROXIMAL_ENERGY,
    )
    # Map aggregated losses to events DataFrame
    # Event losses are stored as power (5-min intervals), divide by 12 to convert to MWh
    # (5 minutes = 1/12 hour)
    df_events["loss"] = df_events.index.map(
        lambda event_id: event_losses_dict.get(event_id, 0.0) / 12
    )
    if df_events.empty:
        grouped_losses = pd.DataFrame(columns=["loss", "name"])
    elif level == "device_type":
        device_type_ids = (
            df_events["device_type_id"].dropna().unique().astype(int).tolist()
        )
        df_device_types = await crud_get_device_types(
            device_type_ids=device_type_ids,
        ).get_async(output_type=OutputType.PANDAS)
        df_device_types = (
            df_device_types.set_index("device_type_id")
            if not df_device_types.empty
            else pd.DataFrame(columns=["name_short", "name_long", "description"])
        )
        grouped_losses = (
            df_events[["device_type_id", "loss"]].groupby("device_type_id").sum()
        )
        grouped_losses["name"] = df_device_types.loc[
            grouped_losses.index,
            "name_long",
        ]
    elif level == "failure_mode":
        failure_mode_ids = (
            df_events["failure_mode_id"].dropna().unique().astype(int).tolist()
        )
        failure_modes_query = get_failure_modes(
            failure_mode_ids=failure_mode_ids,
        )
        data_failure_modes = await failure_modes_query.get_async(
            output_type=OutputType.SQLALCHEMY,
        )
        df_failure_modes = df_from_objects(
            objects=data_failure_modes,
            index_col="failure_mode_id",
        )
        grouped_losses = (
            df_events[["failure_mode_id", "loss"]].groupby("failure_mode_id").sum()
        )
        grouped_losses["name"] = df_failure_modes.loc[
            grouped_losses.index,
            "name_long",
        ]

    grouped_losses["measure"] = "relative"
    grouped_losses = grouped_losses.rename(columns={"loss": "value"})
    grouped_losses["value"] = -grouped_losses["value"]
    grouped_losses = grouped_losses.reset_index(drop=True)
    event_losses_df = grouped_losses
    event_losses_sum = float(event_losses_df["value"].sum())

    # Convert power (W) to energy (MWh): sum of power × time interval / 1,000,000
    # For 5-minute intervals: 5/60 = 1/12 hours
    avg_time_delta_hours = 5 / 60
    expected_energy_mwh = df_expected["value"].sum() * avg_time_delta_hours / 1_000_000

    series_for_budget = crud_pv_budgeted.list_series(
        project_db=project_db,
        project_id=project.project_id,
    )
    budgeted_mwh: float | None = None
    if series_for_budget:
        budgeted_mwh = crud_pv_budgeted.budgeted_energy_mwh_for_operational_window(
            project_db=project_db,
            project_id=project.project_id,
            pv_budgeted_series_id=series_for_budget[0].pv_budgeted_series_id,
            start=start_dt,
            end=end_dt,
            cod=project.cod,
            time_zone=project.time_zone,
        )

    kpi_start, kpi_end_exclusive = _waterfall_kpi_date_range_exclusive_end(
        start_dt=start_dt,
        end_dt=end_dt,
        time_zone=project.time_zone,
    )
    curtailment_agg = await get_project_kpi_data_agg(
        project_id=project.project_id,
        kpi_type_id=KPITypeEnum.PV_PROJECT_CURTAILMENT,
        start=kpi_start,
        end=kpi_end_exclusive,
        aggregation_method="sum",
    ).get_async(output_type=OutputType.SQLALCHEMY)
    curtailment_mwh = float(curtailment_agg or 0.0)
    curtailment_row = pd.DataFrame(
        {
            "value": [-curtailment_mwh],
            "measure": ["relative"],
            "name": ["Curtailment"],
        }
    )

    if budgeted_mwh is not None:
        prefix_frames = [
            pd.DataFrame(
                {
                    "value": [budgeted_mwh],
                    "measure": ["absolute"],
                    "name": ["Budgeted"],
                }
            ),
            pd.DataFrame(
                {
                    "value": [expected_energy_mwh - budgeted_mwh],
                    "measure": ["relative"],
                    "name": ["Weather adjustment"],
                }
            ),
            pd.DataFrame(
                {
                    "value": [expected_energy_mwh],
                    "measure": ["total"],
                    "name": ["PV Expected"],
                }
            ),
        ]
        grouped_losses = pd.concat(
            [*prefix_frames, curtailment_row, event_losses_df]
        ).reset_index(drop=True)
    else:
        new_row = pd.DataFrame(
            {
                "value": [expected_energy_mwh],
                "measure": ["absolute"],
                "name": ["PV Expected"],
            }
        )
        grouped_losses = pd.concat(
            [new_row, curtailment_row, event_losses_df]
        ).reset_index(drop=True)

    # Convert meter power to energy: multiply sum by time interval (5/60 hours
    # for 5-min data)
    avg_meter_time_delta_hours = 5 / 60
    meter_energy_mwh = series_meter.sum() * avg_meter_time_delta_hours
    if budgeted_mwh is not None:
        unaccounted_value = (
            meter_energy_mwh - expected_energy_mwh - event_losses_sum + curtailment_mwh
        )
    else:
        unaccounted_value = meter_energy_mwh - grouped_losses["value"].sum()
    new_row = pd.DataFrame(
        {
            "value": [unaccounted_value],
            "measure": ["relative"],
            "name": ["Unaccounted Difference"],
        }
    )
    grouped_losses = pd.concat([grouped_losses, new_row]).reset_index(drop=True)
    new_row = pd.DataFrame(
        {
            "value": [meter_energy_mwh],
            "measure": ["absolute"],
            "name": ["PV Energy Output"],
        }
    )
    grouped_losses = pd.concat([grouped_losses, new_row]).reset_index(drop=True)

    output = {
        "value": grouped_losses["value"].tolist(),
        "measure": grouped_losses["measure"].tolist(),
        "name": grouped_losses["name"].tolist(),
    }
    return output
