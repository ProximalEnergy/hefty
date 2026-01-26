import datetime
from typing import Annotated

import pandas as pd
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.db_query import OutputType
from core.enumerations import SensorType
from fastapi import Depends, HTTPException
from fastapi.responses import ORJSONResponse
from sqlalchemy.orm import Session

import core
from app import dependencies, utils
from app.v1.protected.web_application.projects.reports.reports import router
from core import models


@router.get("/clearsky-poa", response_class=ORJSONResponse)
async def get_clearsky_poa(
    *,
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    start: datetime.datetime,
    end: datetime.datetime,
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
    project_schema = utils.get_project_schema(project_db=project_db)
    tags_df = await core.crud.project.tags.get_project_tags_v2(
        sensor_type_ids=[SensorType.MET_STATION_POA],
        deep=True,
    ).get_async(
        output_type=OutputType.PANDAS,
        schema=project_schema,
    )
    if tags_df.empty:
        raise HTTPException(
            status_code=404,
            detail="No clearsky tags found.",
        )

    data_timeseries_instance = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_IDS,
        filter_values=tags_df["tag_id"].astype(int).tolist(),
        query_start=start,
        query_end=end,
        project_db=project_db,
    ).get()

    df = data_timeseries_instance.df.to_pandas()
    df = df.set_index("time")
    df.index = pd.to_datetime(df.index).tz_convert(project.time_zone)
    df.columns = df.columns.astype(int)

    if resample_rate is not None:
        df = df.resample(resample_rate).mean()

    device_ids = tags_df["device_id"].astype(int).tolist()
    devices_df = await core.crud.project.devices.get_project_devices(
        device_ids=device_ids,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    device_id_to_name_long = dict(
        zip(
            devices_df["device_id"].astype(int),
            devices_df["name_long"].fillna(""),
        )
    )
    tags_df = tags_df.assign(
        device_name_long=tags_df["device_id"]
        .astype(int)
        .map(device_id_to_name_long)
        .fillna(""),
    )
    tag_id_to_device_name_long = dict(
        zip(tags_df["tag_id"].astype(int), tags_df["device_name_long"])
    )
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
