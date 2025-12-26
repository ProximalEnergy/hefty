import datetime
from typing import Annotated
from uuid import UUID

import pandas as pd
from core.enumerations import SensorType
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import ORJSONResponse
from sqlalchemy.orm import Session

import core
from app import dependencies, utils
from core import models

router = APIRouter(
    prefix="/reports",
    tags=["reports"],
    dependencies=[Depends(dependencies.check_project_access_async)],
    include_in_schema=utils.get_include_in_schema(),
)


@router.get("/clearsky-poa", response_class=ORJSONResponse)
def get_clearsky_poa(
    *,
    project_id: UUID,
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    project_db: Session = Depends(dependencies.get_project_db),
    resample_rate: str | None = "5min",
):
    """todo

    Args:
        project_id: TODO: describe.
        project: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        project_db: TODO: describe.
        resample_rate: TODO: describe.
    """
    if resample_rate is not None:
        rolling_window = int(60 / int(resample_rate.split("min")[0]))
    else:
        rolling_window = 12
    tags = core.crud.project.tags.get_project_tags(
        db=project_db,
        sensor_type_ids=[SensorType.MET_STATION_POA],
        deep=True,
    ).models()
    df = utils.data_df(
        project_db,
        project,
        tags=tags,
        start=start,
        end=end,
        get_last=False,
    )
    if resample_rate is not None:
        df = df.resample(resample_rate).mean()

    device_ids = [tag.device_id for tag in tags]
    devices = core.crud.project.devices.get_project_devices(
        project_db,
        device_ids=device_ids,
    ).models()
    device_id_to_name_long = {device.device_id: device.name_long for device in devices}
    tag_id_to_device_name_long = {
        tag.tag_id: device_id_to_name_long[tag.device_id] for tag in tags
    }
    columns = [
        "POA " + tag_id_to_device_name_long.get(tag_id, tag_id)
        for tag_id in df.columns.astype(int)
    ]
    df.columns = pd.Index(columns)

    df_filtered = df.copy()
    df_filtered = df_filtered[df_filtered > 10]
    df_filtered = df_filtered.dropna(how="all", axis=1).dropna(how="all", axis=0)
    if df_filtered.empty:
        raise HTTPException(
            status_code=404,
            detail="No clearsky data found.",
        )

    df_metrics = pd.DataFrame()

    df_metrics["POA 1D"] = (
        (df_filtered.diff() / 5).rolling(window=rolling_window).mean().mean(axis=1)
    )
    df_metrics["POA 1D Std Dev"] = (
        (df_filtered.diff() / 5).std(axis=1).rolling(window=rolling_window).mean()
    ).fillna(0)

    data_index = pd.DatetimeIndex(df_filtered.index).tz_convert(project.time_zone)
    metrics_index = pd.DatetimeIndex(df_metrics.index).tz_convert(project.time_zone)
    data: list[dict[str, object]] = [
        {
            "x": data_index.tolist(),  # type: ignore
            "y": df_filtered[col].tolist(),
            "name": col,
            "sensor_type_name": None,
            "device_name_long": None,
            "tag_name_scada": None,
            "tag_name_long": col,
        }
        for col in df_filtered.columns
    ]

    data.extend(
        [
            {
                "x": metrics_index.tolist(),  # type: ignore
                "y": df_metrics[col].tolist(),
                "name": col,
                "sensor_type_name": None,
                "device_name_long": None,
                "tag_name_scada": None,
                "tag_name_long": col,
                "line": {"dash": "dash"},
                "yaxis": "y2",
            }
            for col in df_metrics.columns
        ],
    )

    return data
