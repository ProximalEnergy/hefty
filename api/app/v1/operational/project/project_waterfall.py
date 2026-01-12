import datetime
from operator import attrgetter
from typing import Annotated
from uuid import UUID

import pandas as pd
from core.crud.operational.device_types import (
    get_device_types as crud_get_device_types,
)
from core.crud.operational.failure_modes import get_failure_modes
from core.crud.project.event_losses import (
    get_event_losses_aggregated,
)
from core.db_query import OutputType
from core.enumerations import EventLossType, SensorType
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import dependencies, utils
from app._crud.projects.pv_expected import get_pv_expected as crud_get_pv_expected
from core import models

DESCRIPTION_404 = "Tag not found"

router = APIRouter(
    prefix="/projects/{project_id}/waterfall", tags=["project_waterfall"]
)


def df_from_objects(  # nosemgrep: python-enforce-keyword-only-args
    objects: list, index_col: str, time_zone: str | None = None
) -> pd.DataFrame:
    """todo

    Args:
        objects: TODO: describe.
        index_col: TODO: describe.
        time_zone: TODO: describe.
    """
    df = pd.DataFrame.from_records(obj.__dict__ for obj in objects).set_index(index_col)  # type: ignore[arg-type]
    if "_sa_instance_state" in df.columns:
        df = df.drop(columns=["_sa_instance_state"])
    if time_zone is not None:
        df.index = pd.to_datetime(df.index).tz_convert(time_zone)
    return df


@router.get("")
async def get_project_waterfall(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    level: str = "device_type",
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
):
    """todo

    Args:
        project_id: TODO: describe.
        db: TODO: describe.
        project_db: TODO: describe.
        project: TODO: describe.
        level: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
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
        ## PV only
        case 1:
            meter_tags = core.crud.project.tags.get_project_tags(
                db=project_db,
                sensor_type_ids=[SensorType.METER_ACTIVE_POWER],
                deep=True,
            ).models()
            df_meter = utils.data_df(
                project_db,
                project,
                tags=meter_tags,
                start=start,
                end=end,
                get_last=False,
            )
            series_meter = df_meter.iloc[:, 0]
            series_meter.name = "Meter Active Power"
        ## BESS only
        case 2:
            return []
        ## PV + BESS
        case 3:
            meter_tags = core.crud.project.tags.get_project_tags(
                db=project_db,
                sensor_type_ids=[SensorType.PV_MV_CIRCUIT_METER_ACTIVE_POWER],
                deep=True,
            ).models()
            df_meter = utils.data_df(
                project_db,
                project,
                tags=meter_tags,
                start=start,
                end=end,
                get_last=False,
            )
            series_meter = df_meter.sum(axis=1)
            series_meter.name = "Meter Active Power"

    ## Add a series of sequential fallbacks if preferred metric is not available
    ## TODO: integrate this into a table instead
    data_expected = crud_get_pv_expected(
        db=project_db,
        start=start_dt,
        end=end_dt,
        expected_metric_ids=[12],
    )
    if len(data_expected) == 0:
        data_expected = crud_get_pv_expected(
            db=project_db,
            start=start_dt,
            end=end_dt,
            expected_metric_ids=[11],
        )
    if len(data_expected) == 0:
        data_expected = crud_get_pv_expected(
            db=project_db,
            start=start_dt,
            end=end_dt,
            expected_metric_ids=[5],
        )
    if len(data_expected) == 0:
        data_expected = crud_get_pv_expected(
            db=project_db,
            start=start_dt,
            end=end_dt,
            expected_metric_ids=[6],
        )
    if len(data_expected) == 0:
        raise HTTPException(status_code=404, detail="No expected data found")
    df_expected = df_from_objects(data_expected, "time", time_zone=project.time_zone)
    data_events = core.crud.project.events.get_windowed_events(
        project_db, start=start, end=end, deep=True
    ).models()
    df_events = df_from_objects(data_events, "event_id")  # type: ignore
    df_events = df_events.assign(
        device_type_id=df_events["device"].map(attrgetter("device_type_id"))
    )
    # Use aggregated query - much faster than fetching all individual loss records
    event_losses_dict = get_event_losses_aggregated(
        db=project_db,
        time_gte=start,
        time_lt=end,
        event_ids=df_events.index.tolist(),
        event_loss_type_id=EventLossType.PROXIMAL_ENERGY,
    )
    # Map aggregated losses to events DataFrame
    df_events["loss"] = df_events.index.map(
        lambda event_id: event_losses_dict.get(event_id, 0.0)
    )
    if level == "device_type":
        data_device_types = await crud_get_device_types(
            db=db,
            device_type_ids=df_events["device_type_id"].unique().tolist(),
        )
        df_device_types = df_from_objects(data_device_types, "device_type_id")
        grouped_losses = (
            df_events[["device_type_id", "loss"]].groupby("device_type_id").sum()
        )
        grouped_losses["name"] = df_device_types.loc[grouped_losses.index, "name_long"]
    elif level == "failure_mode":
        failure_modes_query = get_failure_modes(
            failure_mode_ids=df_events["failure_mode_id"].unique().tolist(),
        )
        data_failure_modes = await failure_modes_query.get_async(
            output_type=OutputType.SQLALCHEMY,
        )
        df_failure_modes = df_from_objects(data_failure_modes, "failure_mode_id")
        grouped_losses = (
            df_events[["failure_mode_id", "loss"]].groupby("failure_mode_id").sum()
        )
        grouped_losses["name"] = df_failure_modes.loc[grouped_losses.index, "name_long"]

    grouped_losses["measure"] = "relative"
    grouped_losses = grouped_losses.rename(columns={"loss": "value"})
    grouped_losses["value"] = -grouped_losses["value"]
    grouped_losses = grouped_losses.reset_index(drop=True)
    # Calculate expected energy: expected values are power (W) at 5-minute intervals
    # Need to integrate over time: Energy (MWh) = Power (W) × Time (hours) / 1,000,000
    # Calculate time delta in hours from the DataFrame index
    if len(df_expected) > 1:
        # Calculate average time interval between data points
        time_deltas = df_expected.index.to_series().diff().dropna()
        mean_timedelta = time_deltas.mean()  # type: ignore[misc]
        avg_time_delta_hours = pd.Timedelta(mean_timedelta).total_seconds() / 3600
    else:
        # Default to 5 minutes if only one data point
        avg_time_delta_hours = 5 / 60
    # Convert power (W) to energy (MWh): sum of power × time interval / 1,000,000
    # For 5-minute intervals: 5/60 = 1/12 hours
    expected_energy_mwh = df_expected["value"].sum() * avg_time_delta_hours / 1_000_000
    new_row = pd.DataFrame(
        {
            "value": [expected_energy_mwh],
            "measure": ["absolute"],
            "name": ["PV Expected"],
        }
    )
    grouped_losses = pd.concat([new_row, grouped_losses]).reset_index(drop=True)
    # Convert meter power to energy: multiply sum by time interval (5/60 hours
    # for 5-min data)
    if len(series_meter) > 1:
        # Calculate average time interval between data points
        meter_time_deltas = series_meter.index.to_series().diff().dropna()
        mean_meter_timedelta = meter_time_deltas.mean()  # type: ignore[misc]
        avg_meter_time_delta_hours = (
            pd.Timedelta(mean_meter_timedelta).total_seconds() / 3600
        )
    else:
        # Default to 5 minutes if only one data point
        avg_meter_time_delta_hours = 5 / 60
    meter_energy_mwh = series_meter.sum() * avg_meter_time_delta_hours
    new_row = pd.DataFrame(
        {
            "value": -(grouped_losses["value"].sum() - meter_energy_mwh),
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
