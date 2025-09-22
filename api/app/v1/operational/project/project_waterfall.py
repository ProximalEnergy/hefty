import datetime
from operator import attrgetter
from typing import Annotated
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import dependencies, utils
from app._crud.operational.device_types import get_device_types as crud_get_device_types
from app._crud.operational.failure_modes import (
    get_failure_modes as crud_get_failure_modes,
)
from app._crud.projects.pv_expected import get_pv_expected as crud_get_pv_expected
from core import models
from core.database import Base

DESCRIPTION_404 = "Tag not found"

router = APIRouter(
    prefix="/projects/{project_id}/waterfall", tags=["project_waterfall"]
)


def df_from_objects(  # skip-star-syntax
    objects: list[Base], index_col: str, time_zone: str | None = None
) -> pd.DataFrame:
    df = pd.DataFrame.from_records(obj.__dict__ for obj in objects).set_index(index_col)
    if "_sa_instance_state" in df.columns:
        df = df.drop(columns=["_sa_instance_state"])
    if time_zone is not None:
        df.index = pd.to_datetime(df.index).tz_convert(time_zone)
    return df


@router.get("/")
async def get_project_waterfall(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    async_project_db: Annotated[
        AsyncSession, Depends(dependencies.get_project_db_async)
    ],
    project: Annotated[models.Project, Depends(dependencies.get_project)],
    level: str = "device_type",
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
):
    if start is None or end is None:
        start = pd.Timestamp.now(tz=project.time_zone).floor("D") - pd.Timedelta(days=1)
        end = pd.Timestamp.now(tz=project.time_zone).floor("D")
    match project.project_type_id:
        ## PV only
        case 1:
            meter_tags = core.crud.project.tags.get_project_tags(
                db=project_db,
                sensor_type_name_shorts=["meter_active_power"],
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
                sensor_type_name_shorts=["pv_mv_circuit_meter_active_power"],
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
        start=start,
        end=end,
        expected_metric_ids=[12],
    )
    if len(data_expected) == 0:
        data_expected = crud_get_pv_expected(
            db=project_db,
            start=start,
            end=end,
            expected_metric_ids=[11],
        )
    if len(data_expected) == 0:
        data_expected = crud_get_pv_expected(
            db=project_db,
            start=start,
            end=end,
            expected_metric_ids=[5],
        )
    if len(data_expected) == 0:
        data_expected = crud_get_pv_expected(
            db=project_db,
            start=start,
            end=end,
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
    df_event_losses = core.crud.project.event_losses.get_event_losses(
        db=project_db,
        time_gte=start,
        time_lt=end,
        event_ids=df_events.index.tolist(),
    ).pandas_dataframe(index="time", as_datetime=True, tz=project.time_zone)
    if df_event_losses.empty:
        df_event_losses = pd.DataFrame(
            columns=["event_id", "event_loss_type_id", "loss"]
        )
    else:
        df_event_losses = df_event_losses[["event_id", "event_loss_type_id", "loss"]]

    loss_sum = (
        df_event_losses[df_event_losses["event_loss_type_id"] == 1]
        .groupby("event_id", as_index=True)["loss"]
        .sum()
    )
    df_events["loss"] = loss_sum.reindex(df_events.index, fill_value=0)
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
        data_failure_modes = await crud_get_failure_modes(
            db=async_project_db,
            failure_mode_ids=df_events["failure_mode_id"].unique().tolist(),
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
    new_row = pd.DataFrame(
        {
            "value": [df_expected["value"].sum() / 1000000],
            "measure": ["absolute"],
            "name": ["PV Expected"],
        }
    )
    grouped_losses = pd.concat([new_row, grouped_losses]).reset_index(drop=True)
    new_row = pd.DataFrame(
        {
            "value": -(grouped_losses["value"].sum() - series_meter.sum()),
            "measure": ["relative"],
            "name": ["Unaccounted Difference"],
        }
    )
    grouped_losses = pd.concat([grouped_losses, new_row]).reset_index(drop=True)
    new_row = pd.DataFrame(
        {
            "value": [series_meter.sum()],
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
