import datetime
from typing import Annotated

import pandas as pd
from core.db_query import OutputType
from core.enumerations import SensorType
from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse
from pvlib import location
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


@router.get("/degradation-poa", response_class=ORJSONResponse)
async def get_degradation_poa(
    *,
    start: datetime.datetime,
    end: datetime.datetime,
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
):
    """todo

    Args:
        start: TODO: describe.
        end: TODO: describe.
        project: TODO: describe.
        project_db: TODO: describe.
    """
    min_poa = 250
    max_poa_1d = 20
    max_poa_std = 7.5
    max_poa_std_1d = 2.5
    start = pd.to_datetime(start).tz_convert(project.time_zone)
    end = pd.to_datetime(end).tz_convert(project.time_zone)
    lon, lat = project.point.coordinates  # type: ignore
    site = location.Location(lat, lon, tz=project.time_zone)

    tracking_df = utils.get_tracking_angles(
        site_location=site,
        start=start,
        end=end,
        freq="5min",
    )
    theoretical_poa = utils.get_truetracking_irradiance(
        site_location=site,
        start=start,
        end=end,
        tilt=tracking_df["tracker_theta"].abs(),
        surface_azimuth=tracking_df["surface_azimuth"],
    )

    tags = core.crud.project.tags.get_project_tags(
        db=project_db,
        sensor_type_ids=[SensorType.MET_STATION_POA],
        deep=True,
    ).models()
    df_raw = utils.data_df(
        project_db,
        project,
        tags=tags,
        start=start,
        end=end,
        get_last=False,
    )
    df_raw.index = pd.to_datetime(df_raw.index).tz_convert(project.time_zone)
    df_raw = df_raw.resample("5min").ffill()
    df_raw = df_raw.reindex(
        pd.date_range(start=start, end=end - pd.Timedelta(minutes=5), freq="5min"),
    )
    df_raw.columns = df_raw.columns.get_level_values(0)
    df_raw = df_raw.sort_index(axis=1)
    df_raw.columns.name = "tag_id"

    df = df_raw.copy()

    df = df[df > 10]
    df = df.dropna(how="all", axis=1).dropna(how="all", axis=0)

    trkr_scores = (~df[df.gt(theoretical_poa["poa_global"], axis=0)].isna()).sum()

    bad_trackers = trkr_scores[trkr_scores < trkr_scores.mean() * 0.9].index
    df = df.drop(columns=bad_trackers)

    df_1d = df.diff(periods=1).abs() + df.diff(periods=-1).abs()  # type: ignore[operator]
    df_1d_std = df_1d.std(axis=1).rolling(3, center=True).mean()
    df_1d_std_left = df_1d_std.diff(periods=1).abs()
    df_1d_std_right = df_1d_std.diff(periods=-1).abs()
    df_1d_std_1d = df_1d_std_left + df_1d_std_right  # type: ignore[operator]

    irr_idx = df.median(axis=1) < min_poa
    der_idx = df_1d.mean(axis=1) > max_poa_1d
    std_idx = df_1d_std > max_poa_std
    std_1d_idx = df_1d_std_1d > max_poa_std_1d  # type: ignore
    changing_idx = df.diff(periods=1).abs().sum(axis=1) < 0.1
    bad_idx = (std_idx & std_1d_idx) | irr_idx | der_idx | changing_idx

    df_filtered = df.loc[~bad_idx]

    device_ids = [tag.device_id for tag in tags]
    project_schema = utils.get_project_schema(project_db=project_db)
    devices_df = await core.crud.project.devices.get_project_devices(
        device_ids=device_ids,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    device_id_to_name_long = dict(
        zip(
            devices_df["device_id"].astype(int),
            devices_df["name_long"].fillna(""),
        )
    )
    tag_id_to_device_name_long = {
        tag.tag_id: device_id_to_name_long[tag.device_id] for tag in tags
    }
    columns = {
        x: y
        for x, y in zip(
            df_raw.columns,
            [
                "POA " + tag_id_to_device_name_long.get(tag_id, tag_id)
                for tag_id in df_raw.columns.astype(int)
            ],
        )
    }

    df = df.rename(columns=columns)
    df_raw = df_raw.rename(columns=columns)
    df_filtered = df_filtered.rename(columns=columns)

    data_index = pd.DatetimeIndex(df_raw.index).tz_convert(project.time_zone)
    data: dict[str, object] = {
        "data": [
            {
                "x": data_index.tolist(),  # type: ignore
                "y": df_raw[col].tolist(),
                "name": col,
                "sensor_type_name": None,
                "device_name_long": None,
                "tag_name_scada": None,
                "tag_name_long": col,
            }
            for col in df_raw.columns
        ],
    }

    filtered_index = pd.DatetimeIndex(df_filtered.index).tz_convert(
        project.time_zone,
    )
    data["valid_indexes"] = filtered_index.tolist()  # type: ignore[attr-defined]
    data["valid_columns"] = df_filtered.columns.tolist()

    return data
