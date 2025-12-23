################################################################################
#                                                                              #
#  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!  #
#  !                                                                        !  #
#  !  DEPRECATION WARNING: This file is deprecated and will be removed      !  #
#  !  in a future release.  Please do not add new code here.  All new       !  #
#  !  additions should be placed in protected.                              !  #
#  !                                                                        !  #
#  !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!  #
#                                                                              #
################################################################################
import datetime
import json
import logging
import mimetypes
import time
from io import BytesIO
from typing import Annotated
from uuid import UUID

import boto3
import numpy as np
import pandas as pd
from botocore.config import Config
from core.dependencies import get_db
from core.enumerations import DeviceType, SensorType
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import ORJSONResponse
from natsort import natsort_keygen, natsorted
from pvlib import location
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import dependencies, interfaces, logger, utils
from app._crud.operational.cec_pv_modules import get_cec_pv_modules
from app._crud.operational.pv_modules import get_pv_modules
from app.utils import get_include_in_schema
from app.v1.analytics.gis import router as gis_router
from core import models

router = APIRouter(
    prefix="/analytics/{project_id}",
    dependencies=[
        Depends(dependencies.check_project_access_async),
    ],
    tags=["analytics"],
    include_in_schema=get_include_in_schema(),
)
router.include_router(gis_router)


@router.get(
    "/gis/combiner/{block_device_id}",
    response_model=interfaces.GeoJSON,
    response_class=ORJSONResponse,
)
def get_combiner_block_performance(
    block_device_id: int,
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
):
    # Query data for the last 30 minutes (offset by 5 minutes)
    """todo

    Args:
        block_device_id: TODO: describe.
        project_db: TODO: describe.
        project: TODO: describe.
    """
    end = pd.Timestamp.utcnow().floor("5min")
    start = end - pd.Timedelta(minutes=30)

    # Get requested pv_block device
    device_block = core.crud.project.devices.get_project_device(
        db=project_db, device_id=block_device_id, deep=False
    ).model()

    if device_block is None:
        raise HTTPException(
            status_code=404,
            detail="Block device not found",
        )

    # Get descendent pv_dc_combiner devices of requests pv_block
    devices_combiner = core.crud.project.devices.get_project_devices(
        db=project_db,
        device_type_ids=[DeviceType.PV_DC_COMBINER],
        device_id_descendent_of=device_block.device_id,
    ).models()

    # Get tags for combiner current
    tags = core.crud.project.tags.get_project_tags(
        project_db,
        sensor_type_ids=[SensorType.PV_DC_COMBINER_CURRENT],
        device_ids=[d.device_id for d in devices_combiner],
    ).models()

    # Get data for combiner current
    try:
        df = utils.data_df(
            project_db,
            project,
            tags,
            start=start,
            end=end,
            fillna_zero=False,
        )
        missing_data = False

        # Drop all rows that have all NaNs
        df = df.dropna(how="all")

        if len(df) == 0:
            missing_data = True
    except HTTPException:
        missing_data = True

    if not missing_data:
        # Rename columns from tags to device ids
        # NOTE: These device ids are combiner device ids
        tag_id_to_device_id = {tag.tag_id: tag.device_id for tag in tags}
        df.columns = pd.Index(
            [tag_id_to_device_id[tag_id] for tag_id in df.columns.astype(int)]
        )

        timestamp = df.index[-1].isoformat()
        max_current = df.tail(1).max().max()

    else:
        timestamp = (end - pd.Timedelta(minutes=5)).isoformat()
        max_current = 1

    features = [
        {
            "type": "Feature",
            "properties": {
                "timestamp": timestamp,
                # TODO: This needs to be better than just grabbing the last value
                "combiner_current": (
                    df[device.device_id].iloc[-1] if not missing_data else np.nan
                ),
                "combiner_name": device.name_long,
                "block_name": device_block.name_long,
                "max_current": max_current,
            },
            "geometry": device.polygon,
        }
        for device in devices_combiner
    ]

    return_data = {
        "type": "FeatureCollection",
        "features": features,
    }

    return return_data


@router.get("/heatmap/{sensor_type_name_short}", response_class=ORJSONResponse)
def get_heatmap(
    project_id: UUID,
    sensor_type_name_short: str,
    db: Annotated[Session, Depends(get_db)],
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: models.Project = Depends(dependencies.get_project_api),
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    agg: str = "instantaneous",
    fillna_zero: bool = True,
):
    """todo

    Args:
        project_id: TODO: describe.
        sensor_type_name_short: TODO: describe.
        db: TODO: describe.
        project_db: TODO: describe.
        project: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        agg: TODO: describe.
        fillna_zero: TODO: describe.
    """
    tags = core.crud.project.tags.get_project_tags(
        project_db,
        sensor_type_name_shorts=[sensor_type_name_short],
        deep=False,
    ).models()

    if len(tags) == 0:
        tags = core.crud.project.tags.get_project_tags(
            project_db,
            sensor_type_ids=[SensorType.PV_PCS_MODULE_AC_POWER],
        ).models()

    if len(tags) == 0:
        raise HTTPException(status_code=404, detail="No tags found")

    if start is None:
        start = pd.Timestamp.utcnow().floor("5min") - pd.DateOffset(days=1)
    if end is None:
        end = pd.Timestamp.utcnow().floor("5min")

    df = utils.data_df(
        project_db,
        project,
        tags,
        start=start,
        end=end,
        agg=agg,
        fillna_zero=fillna_zero,
    )

    device_ids = [tag.device_id for tag in tags]
    devices = core.crud.project.devices.get_project_devices(
        project_db,
        device_ids=device_ids,
    ).models()

    device_id_to_name_long = {device.device_id: device.name_long for device in devices}
    tag_id_to_device_name_long = {
        tag.tag_id: device_id_to_name_long[tag.device_id] for tag in tags
    }

    # Rename and sort columns
    columns = df.columns.astype(int).tolist()
    columns = [tag_id_to_device_name_long.get(tag_id, tag_id) for tag_id in columns]
    df.columns = pd.Index(columns)
    df = df[natsorted(df.columns)]

    # Get list of timestamps
    timestamps = df.index.tz_convert(project.time_zone).tolist()  # type: ignore

    # Get list of column names
    columns = df.columns.tolist()

    # Get list of values
    values = df.T.values.tolist()

    return {
        "x": timestamps,
        "y": columns,
        "z": values,
    }


@router.get("/clearsky-poa", response_class=ORJSONResponse)
def get_clearsky_poa(
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
    # df_metrics["POA 2D"] = (
    #     ((df_filtered.diff() / 5).diff() / 5)
    #     .rolling(window=rolling_window)
    #     .mean()
    #     .mean(axis=1)
    # )
    df_metrics["POA 1D Std Dev"] = (
        (df_filtered.diff() / 5).std(axis=1).rolling(window=rolling_window).mean()
    ).fillna(0)

    # Replace inf and -inf with None (which will be serialized as null in JSON)
    # df_filtered = df_filtered.replace([np.inf, -np.inf, np.nan], None)
    data = [
        {
            "x": df_filtered.index.tz_convert(project.time_zone).tolist(),  # type: ignore
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
                "x": df_metrics.index.tz_convert(project.time_zone).tolist(),  # type: ignore
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

    # Sort data by tag_name_long using natsorted
    # data = natsorted(data, key=lambda x: x["tag_name_long"])
    return data


@router.get("/degradation-poa", response_class=ORJSONResponse)
def get_degradation_poa(
    project_id: UUID,
    start: datetime.datetime,
    end: datetime.datetime,
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
):
    """todo

    Args:
        project_id: TODO: describe.
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
    df_1d_std_1d = df_1d_std.diff(periods=1).abs() + df_1d_std.diff(periods=-1).abs()  # type: ignore[operator]

    irr_idx = df.median(axis=1) < min_poa
    der_idx = df_1d.mean(axis=1) > max_poa_1d
    std_idx = df_1d_std > max_poa_std
    std_1d_idx = df_1d_std_1d > max_poa_std_1d  # type: ignore
    changing_idx = df.diff(periods=1).abs().sum(axis=1) < 0.1
    bad_idx = (std_idx & std_1d_idx) | irr_idx | der_idx | changing_idx

    df_filtered = df.loc[~bad_idx]

    device_ids = [tag.device_id for tag in tags]
    devices = core.crud.project.devices.get_project_devices(
        project_db,
        device_ids=device_ids,
    ).models()
    device_id_to_name_long = {device.device_id: device.name_long for device in devices}
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

    data = {
        "data": [
            {
                "x": df_raw.index.tz_convert(project.time_zone).tolist(),  # type: ignore
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

    data["valid_indexes"] = df_filtered.index.tz_convert(project.time_zone).tolist()  # type: ignore[attr-defined]
    data["valid_columns"] = df_filtered.columns.tolist()  # type: ignore[assignment]

    return data


@router.get("/dc-amperage-report-v2")
async def dc_amperage_report_v2(
    project_id: str,
    start: datetime.datetime,
    min_poa: float,
    max_poa_1d: float,
    max_poa_std: float,
    rolling_window: int,
    use_poa_1d: bool,
    use_poa_std: bool,
    resample_rate: str = "5min",
    db: AsyncSession = Depends(dependencies.get_async_db),
    project_db: Session = Depends(dependencies.get_project_db),
    async_project_db: AsyncSession = Depends(dependencies.get_project_db_async),
    project: models.Project = Depends(dependencies.get_project_api),
):
    """todo

    Args:
        project_id: TODO: describe.
        start: TODO: describe.
        min_poa: TODO: describe.
        max_poa_1d: TODO: describe.
        max_poa_std: TODO: describe.
        rolling_window: TODO: describe.
        use_poa_1d: TODO: describe.
        use_poa_std: TODO: describe.
        resample_rate: TODO: describe.
        db: TODO: describe.
        project_db: TODO: describe.
        async_project_db: TODO: describe.
        project: TODO: describe.
    """
    logger.logger.info("DC Amperage Report V2 Endpoint Starting")

    project_tz = project.time_zone
    start = pd.Timestamp(start).tz_convert(None).normalize()
    start_date = start.tz_localize(project_tz)
    end_date = start_date + pd.Timedelta(days=1)

    logger.logger.info("POA tags")
    poa_tags = core.crud.project.tags.get_project_tags(
        project_db,
        sensor_type_ids=[SensorType.MET_STATION_POA],
    ).models()

    logger.logger.info("POA data")
    df_poa = utils.data_df(
        project_db,
        project,
        poa_tags,
        start=start_date,
        end=end_date,
    )

    df_poa = df_poa.resample(resample_rate).mean()

    logger.logger.info("POA data processing")
    # Keep data where irradiance is above 10
    df_poa = df_poa[df_poa > 10]

    # Drop all columns and rows that are all NaN
    # TODO: Does dropping rows impact the first derivative calculation?
    df_poa = df_poa.dropna(how="all", axis=1).dropna(how="all", axis=0)

    # Calculate first derivative
    # NOTE: Divide by 5 to convert to 1-minute rate of change
    df_poa_1d = df_poa.diff() / 5

    # Calculate standard deviation
    df_poa_1d_std = df_poa_1d.std(axis=1)
    if df_poa_1d.shape[1] == 1:
        # If there's only one column, the std is NaN. Replace with 0.
        df_poa_1d_std = df_poa_1d_std.fillna(0)
    df_poa_1d_std = df_poa_1d_std.interpolate().rolling(window=rolling_window).mean()

    # Apply rolling window to first derivative
    df_poa_1d = df_poa_1d.rolling(window=rolling_window).mean().mean(axis=1).abs()  # type: ignore

    # Apply filters
    df_poa = df_poa[
        (df_poa.mean(axis=1) > min_poa)
        & (df_poa_1d < max_poa_1d if use_poa_1d else True)
        & (df_poa_1d_std < max_poa_std if use_poa_std else True)
    ]

    logger.logger.info("CB tags")
    tags_cb = core.crud.project.tags.get_project_tags(
        project_db,
        sensor_type_ids=[SensorType.PV_DC_COMBINER_CURRENT],
    ).models()
    if len(tags_cb) == 0:
        raise HTTPException(
            status_code=404, detail="No combiner boxes configured for this project"
        )
    df_tags_cb = pd.DataFrame([x.__dict__ for x in tags_cb]).set_index(
        "tag_id",
        drop=True,
    )

    logger.logger.info("CB data")
    df_cb = utils.data_df(project_db, project, tags_cb, start=start_date, end=end_date)

    logger.logger.info("CB data processing")

    devices = core.crud.project.devices.get_project_devices(
        project_db,
        device_type_ids=[
            DeviceType.PV_PCS,
            DeviceType.MET_STATION,
            DeviceType.PV_DC_COMBINER,
        ],
        deep=False,
    ).models()

    inv_devices = [d for d in devices if d.device_type_id == DeviceType.PV_PCS]
    inv_devices_df = pd.DataFrame([x.__dict__ for x in inv_devices]).set_index(
        "device_id",
        drop=True,
    )

    cb_devices = [d for d in devices if d.device_type_id == DeviceType.PV_DC_COMBINER]
    df_cb_report = pd.DataFrame([x.__dict__ for x in cb_devices]).set_index(
        "device_id",
        drop=True,
    )

    met_devices = [d for d in devices if d.device_type_id == DeviceType.MET_STATION]

    # NOTE: This df_cb_report will be transformed until writing to Excel

    pv_dc_combiners = core.crud.project.pv_dc_combiners.get_pv_dc_combiners(
        project_db
    ).models()
    cb_device_id_to_modules_per_pv_source_circuit = {
        x.device_id: x.modules_per_pv_source_circuit for x in pv_dc_combiners
    }

    # Query either CEC or local database for modules in the report
    if df_cb_report["pv_module_id"].unique().tolist() != [None]:
        pv_modules = await get_pv_modules(
            db=async_project_db,
            pv_module_ids=df_cb_report["pv_module_id"].unique().tolist(),
        )
        pv_modules_df = pd.DataFrame([x.__dict__ for x in pv_modules]).set_index(
            "pv_module_id",
            drop=True,
        )
        # Calculate Voltage at max power
        df_cb_report["Vmp"] = df_cb_report["pv_module_id"].map(pv_modules_df["vmp"])
        df_cb_report["pmax"] = df_cb_report["pv_module_id"].map(pv_modules_df["pmax"])

    else:
        pv_modules = await get_cec_pv_modules(
            db,
            cec_pv_module_ids=df_cb_report["cec_pv_module_id"].unique().tolist(),
        )
        pv_modules_df = pd.DataFrame([x.__dict__ for x in pv_modules]).set_index(
            "cec_pv_module_id",
            drop=True,
        )
        df_cb_report["Vmp"] = df_cb_report["cec_pv_module_id"].map(
            pv_modules_df["nameplate_vpmax"],
        )
        df_cb_report["pmax"] = df_cb_report["cec_pv_module_id"].map(
            pv_modules_df["nameplate_pmax"],
        )

    # Sort by combiner name
    df_cb_report = df_cb_report.sort_values("name_long", key=natsort_keygen())  # type: ignore

    # Bring in strings per combiner
    df_cb_report["strings_per_cb"] = df_cb_report.index.map(
        cb_device_id_to_modules_per_pv_source_circuit,
    )

    # Define parent inverter name
    df_cb_report["Parent Inverter"] = df_cb_report["parent_device_id"].map(
        inv_devices_df["name_long"],
    )

    # Calculate string Voltage at max power
    df_cb_report["string_Vmp"] = df_cb_report["Vmp"] * df_cb_report["strings_per_cb"]

    # Calculate nominal string current
    df_cb_report["a_nom"] = (
        df_cb_report["capacity_dc"] * 1000 / df_cb_report["string_Vmp"]
    )

    # Calculate average current for each combiner
    cb_series_means = df_cb.loc[df_poa.index].mean()
    tag_to_device = df_tags_cb.loc[df_cb.columns, "device_id"].to_dict()
    cb_series_means = cb_series_means.rename(index=tag_to_device)
    df_cb_report["a_avg"] = cb_series_means

    # Calculate normalized current by dividing average current by nominal current
    df_cb_report["a_norm"] = df_cb_report["a_avg"] / df_cb_report["a_nom"]

    # Calculate a_median and a_norm_adj for each inverter group
    df_cb_report["a_median"] = df_cb_report["Parent Inverter"].map(
        df_cb_report.groupby("Parent Inverter")["a_norm"].median(),
    )
    df_cb_report["a_norm_adj"] = (
        df_cb_report["a_norm"] / df_cb_report["a_median"]
    ).fillna(0)

    df_cb_report["a_median_proj"] = df_cb_report["a_norm"].median()
    df_cb_report["a_norm_proj"] = df_cb_report["a_norm"] / df_cb_report["a_median_proj"]

    logger.logger.info("Preparing for export")
    df_cb_report = df_cb_report.rename(
        columns={
            "name_long": "Combiner Name",
            "capacity_dc": "kW",
            "pmax": "BIN Class",
        },
    )
    df_cb_report = df_cb_report[
        [
            "Parent Inverter",
            "Combiner Name",
            "BIN Class",
            "kW",
            "Vmp",
            "strings_per_cb",
            "string_Vmp",
            "a_nom",
            "a_avg",
            "a_norm",
            "a_median",
            "a_median_proj",
            "a_norm_adj",
            "a_norm_proj",
        ]
    ]

    index_map = (
        df_tags_cb[["device_id", "name_scada"]]
        .set_index("device_id")
        .to_dict()["name_scada"]
    )
    df_cb_report = df_cb_report.rename(index=index_map)
    df_cb_report.index.name = "Combiner SCADA"

    df_return = df_cb_report[
        ["Parent Inverter", "Combiner Name", "a_norm_adj", "a_norm_proj"]
    ].copy()
    df_return["Combiner Name"] = df_return["Combiner Name"].str.split(".").str[1]

    df_return["Combiner Enumeration"] = (
        (df_return.groupby("Parent Inverter").cumcount() + 1).astype(str).str.zfill(2)
    )

    df_return_inv = df_return.pivot(
        index="Combiner Enumeration",
        columns="Parent Inverter",
        values="a_norm_adj",
    )
    df_return_proj = df_return.pivot(
        index="Combiner Enumeration",
        columns="Parent Inverter",
        values="a_norm_proj",
    )

    df_return_inv = df_return_inv.replace([np.nan, np.inf, -np.inf], None)
    df_return_proj = df_return_proj.replace([np.nan, np.inf, -np.inf], None)

    # punch_list = df_cb_report.loc[
    #     (df_cb_report["a_norm_adj"] > 1.1)
    #     | ((df_cb_report["a_norm_adj"] < 0.9) & (df_cb_report["a_norm_adj"] > 0))
    #     | (df_cb_report["a_norm_adj"] > 1.05)
    #     | ((df_cb_report["a_norm_adj"] < 0.95) & (df_cb_report["a_norm_adj"] > 0)),
    #     "Combiner Name",
    # ].values.tolist()
    # punch_list = natsorted(list(set(punch_list)))
    # df_punch_list_performance = pd.DataFrame(data={"Combiner": punch_list})
    df_punch_list_performance = df_cb_report.loc[
        (df_cb_report["a_norm_adj"] > 1.1)
        | ((df_cb_report["a_norm_adj"] < 0.9) & (df_cb_report["a_norm_adj"] > 0))
        | (df_cb_report["a_norm_adj"] > 1.05)
        | ((df_cb_report["a_norm_adj"] < 0.95) & (df_cb_report["a_norm_adj"] > 0)),
        ["Combiner Name", "a_norm_adj", "a_norm_proj"],
    ]
    df_punch_list_performance = df_punch_list_performance.reset_index(drop=True)
    df_punch_list_performance = df_punch_list_performance.rename(
        columns={
            "a_norm_adj": "Inverter Normalized",
            "a_norm_proj": "Project Normalized",
        },
    )

    punch_list = df_cb_report.loc[
        (df_cb_report["a_norm_proj"] == 0),
        "Combiner Name",
    ].values.tolist()
    punch_list = natsorted(list(set(punch_list)))
    df_punch_list_offline = df_cb_report[
        df_cb_report["Combiner Name"].isin(punch_list)
    ][["Parent Inverter", "Combiner Name"]]

    # Group by Parent Inverter and count combiners
    inverter_combiner_counts = df_cb_report.groupby("Parent Inverter")[
        "Combiner Name"
    ].count()

    # Count offline combiners per inverter
    offline_combiner_counts = df_punch_list_offline.groupby("Parent Inverter")[
        "Combiner Name"
    ].count()

    # Identify inverters where all combiners are offline
    offline_inverters = []
    for inverter in inverter_combiner_counts.index:
        total_combiners = inverter_combiner_counts.get(inverter, 0)
        offline_combiners = offline_combiner_counts.get(inverter, 0)
        if total_combiners > 0 and total_combiners == offline_combiners:
            offline_inverters.append(inverter)

    offline_single_combiners = df_punch_list_offline[
        ~df_punch_list_offline["Parent Inverter"].isin(offline_inverters)
    ]["Combiner Name"].values.tolist()
    df_punch_list_offline_invs = pd.DataFrame(data={"Combiner": offline_inverters})
    df_punch_list_offline_cbs = pd.DataFrame(
        data={"Combiner": offline_single_combiners},
    )

    df_metadata = pd.DataFrame(
        data={
            "Parameter": [
                "Clearsky Filters",
                "min_poa",
                "max_poa_1d",
                "max_poa_std",
                "rolling_window",
                "start",
                "end",
                "num_periods",
                "Columns in DC Amperage Check",
                "BIN Class",
                "kW",
                "Vmp",
                "strings_per_cb",
                "string_Vmp",
                "a_nom",
                "a_avg",
                "a_norm",
                "a_median",
                "a_median_proj",
                "a_norm_adj",
                "a_norm_proj",
                "Sheet Descriptions",
                "DC Amperage Check",
                "Punch List (Performance)",
                "Punch List (Offline CBs)",
                "Punch List (Offline Invs)",
                "Matrix (Inv)",
                "Matrix (Proj)",
            ],
            "Value": [
                None,
                min_poa,
                max_poa_1d if use_poa_1d else None,
                max_poa_std if use_poa_std else None,
                rolling_window,
                start_date.tz_localize(None),
                end_date.tz_localize(None),
                df_poa.shape[0],
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            ],
            "Description": [
                None,
                "Minimum POA irradiance for clear sky period",
                "Maximum 1-minute POA first derivative for clear sky period",
                "Maximum rolling window standard deviation of POA irradiance for clear sky period",
                "Number of 5-minute periods for rolling window",
                "Analysis Start Period",
                "Analysis End Period",
                "Number of 5-minute periods included in analysis after filters applied",
                None,
                "BIN Class for modules associated with combiner (W)",
                "Nominal DC Power (kW)",
                "Module Vmp (V), retrieved from CEC database",
                "Number of strings per combiner box",
                "String Vmp (Vmp * strings_per_cb)",
                "Nominal string current (A)",
                "Average combiner box current (A)",
                "Combiner box current as a percent of nominal current",
                "Median value of a_norm as found across combiners in the parent inverter",
                "Median value of a_norm as found across combiners in the entire project",
                "Combiner box current as a percent of median current across the parent inverter",
                "Combiner box current as a percent of median current across the entire project",
                None,
                "Main DC analysis sheet with normalized values for each combiner",
                "Punch list of combiners which are performing outside of acceptance criteria",
                "Punch list of combiners which are offline, but whose parent inverter is online",
                "Punch list of parent inverters which have all combiners offline",
                "Matrix of combiner current as a percent of nominal current for each parent inverter (5% threshold)",
                "Matrix of combiner current as a percent of median current for entire project (10% threshold)",
            ],
        },
    )

    def highlight_style(*, val, col, subset: bool = False):
        """todo

        Args:
            val: TODO: describe.
            col: TODO: describe.
            subset: TODO: describe.
        """
        if subset:
            if col == "a_norm_proj":
                if val > 1.1:
                    return "background-color: #60497A; color: #FFFFFF;"
                elif val < 0.9:
                    return "background-color: #FFC7CE; color: #9C0006;"
            elif col == "a_norm_adj":
                if val > 1.05:
                    return "background-color: #60497A; color: #FFFFFF;"
                elif val < 0.95:
                    return "background-color: #FFC7CE; color: #9C0006;"
            return ""
        else:
            try:
                if val > 1.05:
                    return "background-color: #60497A; color: #FFFFFF;"
                elif val < 0.95:
                    return "background-color: #FFC7CE; color: #9C0006;"
                return ""
            except TypeError:
                return ""

    # Create a BytesIO object to store the Excel file in memory
    logger.logger.info("Excel writing")
    excel_buffer = BytesIO()
    poa_buffer = BytesIO()
    cb_buffer = BytesIO()

    with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
        workbook = writer.book

        # Add formats to the workbook as needed
        # bold_format = workbook.add_format({'bold': True})
        # center_format = workbook.add_format({'align': 'center'})
        # wrap_format = workbook.add_format({'text_wrap': True})
        # grey_fill_format = workbook.add_format({'bg_color': '#D3D3D3'})
        # bold_center_format = workbook.add_format({'bold': True, 'align': 'center'})
        bold_center_grey_format = workbook.add_format(
            {"bold": True, "align": "center", "bg_color": "#D3D3D3"},
        )

        # Write dataframes to Excel with styles applied via pandas Styler
        df_metadata.to_excel(
            writer,
            sheet_name="Analysis Metadata",
            index=False,
            header=True,
        )
        df_cb_report.style.apply(
            lambda x: [
                highlight_style(val=v, col=col, subset=True)
                for v, col in zip(x, x.index)
            ],
            subset=["a_norm_proj", "a_norm_adj"],
            axis=1,
        ).to_excel(writer, sheet_name="DC Amperage Check", index=True)
        # df_poa_out.style.apply(lambda x: df_poa_style, axis=None).to_excel(
        #     writer, sheet_name="POA", index=True
        # )
        # df_cb_data_out.style.apply(lambda x: df_cb_data_style, axis=None).to_excel(
        #     writer, sheet_name="RAW", index=True
        # )
        df_punch_list_performance.to_excel(
            writer,
            sheet_name="Punch List (Performance)",
            index=True,
        )
        df_punch_list_offline_cbs.to_excel(
            writer,
            sheet_name="Punch List (Offline CBs)",
            index=True,
        )
        df_punch_list_offline_invs.to_excel(
            writer,
            sheet_name="Punch List (Offline Invs)",
            index=True,
        )
        df_return_inv.style.apply(
            lambda x: [highlight_style(val=v, col=col) for v, col in zip(x, x.index)],
        ).to_excel(writer, sheet_name="Matrix (Inv)", index=True)
        df_return_proj.style.apply(
            lambda x: [highlight_style(val=v, col=col) for v, col in zip(x, x.index)],
        ).to_excel(writer, sheet_name="Matrix (Proj)", index=True)

        # Access worksheets
        # dc_sheet = writer.sheets["DC Amperage Check"]
        # poa_sheet = writer.sheets["POA"]
        # raw_sheet = writer.sheets["RAW"]
        # plp_sheet = writer.sheets["Punch List (Performance)"]
        # plo_sheet = writer.sheets["Punch List (Offline CBs)"]
        # pli_sheet = writer.sheets["Punch List (Offline Invs)"]
        meta_sheet = writer.sheets["Analysis Metadata"]

        # Merge cells and apply formatting on meta_sheet
        # For A2:C2 (zero-based indices: row 1, columns 0-2)
        meta_sheet.merge_range(
            1,
            0,
            1,
            2,
            df_metadata.iloc[0, 0],
            bold_center_grey_format,
        )
        # For A10:C10 (zero-based indices: row 9, columns 0-2)
        meta_sheet.merge_range(
            9,
            0,
            9,
            2,
            df_metadata.iloc[8, 0],
            bold_center_grey_format,
        )
        # For A23:C23 (zero-based indices: row 22, columns 0-2)
        meta_sheet.merge_range(
            22,
            0,
            22,
            2,
            df_metadata.iloc[21, 0],
            bold_center_grey_format,
        )

        # Auto-fit column width for certain sheets
        auto_fit_sheets = {
            "DC Amperage Check": df_cb_report,
            "Punch List (Performance)": df_punch_list_performance,
            "Punch List (Offline CBs)": df_punch_list_offline_cbs,
            "Punch List (Offline Invs)": df_punch_list_offline_invs,
            "Analysis Metadata": df_metadata,
        }
        for sheet_name, dataframe in auto_fit_sheets.items():
            worksheet = writer.sheets[sheet_name]
            for idx, col in enumerate(dataframe.columns):
                series = dataframe[col]
                max_len = (
                    max(series.astype(str).map(len).max(), len(str(series.name))) + 2
                )  # Adding a little extra space
                worksheet.set_column(idx, idx, max_len)

        # Set all column widths to 18 for certain sheets and enable word wrap for headers
        # for sheet_name in ["POA", "RAW"]:
        #     worksheet = writer.sheets[sheet_name]
        #     worksheet.set_column(0, len(df_poa_out.columns) - 1, 18)
        #     header_format = workbook.add_format({'text_wrap': True, 'align': 'center'})
        #     worksheet.set_row(0, None, header_format)

        # Insert image into poa_sheet
        # img_col = df_poa_out.shape[1]  # Zero-based index
        # img_row = 1  # Zero-based index for the second row
        # poa_sheet.insert_image(img_row, img_col, img_buffer)

    def rename_poa_columns(*, df_poa, poa_tags, met_devices):
        # Create mappings for easier lookup
        """todo

        Args:
            df_poa: TODO: describe.
            poa_tags: TODO: describe.
            met_devices: TODO: describe.
        """
        tag_to_device_id = {tag.tag_id: tag.device_id for tag in poa_tags}
        device_id_to_name_short = {
            device.device_id: device.name_short for device in met_devices
        }

        # Map columns in df_poa to "Met Station POA {name_short}"
        new_columns = [
            (
                f"Met Station POA {device_id_to_name_short[tag_to_device_id[col]]}"
                if col in tag_to_device_id
                and tag_to_device_id[col] in device_id_to_name_short
                else f"Unknown POA {col}"
            )  # Fallback for missing mappings
            for col in df_poa.columns
        ]

        # Rename the columns
        return df_poa.rename(
            columns={x: y for x, y in zip(df_poa.columns, new_columns)},
        )

    def rename_cb_columns(*, df_cb, met_devices):
        # Create mappings for easier lookup
        """todo

        Args:
            df_cb: TODO: describe.
            met_devices: TODO: describe.
        """
        tag_to_device_id = {tag.tag_id: tag.device_id for tag in tags_cb}
        device_id_to_name_long = {
            device.device_id: device.name_long for device in cb_devices
        }

        new_columns = [
            (
                f"Combiner Current {device_id_to_name_long[tag_to_device_id[col]]}"
                if col in tag_to_device_id
                and tag_to_device_id[col] in device_id_to_name_long
                else f"Unknown Combiner {col}"
            )
            for col in df_cb.columns
        ]

        return df_cb.rename(columns={x: y for x, y in zip(df_cb.columns, new_columns)})

    # Example usage:
    df_poa = rename_poa_columns(
        df_poa=df_poa,
        poa_tags=poa_tags,
        met_devices=met_devices,
    )
    df_poa.columns = pd.Index(natsorted(df_poa.columns))

    df_cb = rename_cb_columns(df_cb=df_cb, met_devices=cb_devices)
    df_cb.columns = pd.Index(natsorted(df_cb.columns))

    # Function to upload a file to S3 and generate a presigned URL
    def upload_to_s3_and_generate_url(
        *,
        s3_client,
        buffer,
        bucket_name,
        prefix,
        filename,
        tags="temporary",
    ):
        # Reset the buffer position to the beginning
        """todo

        Args:
            s3_client: TODO: describe.
            buffer: TODO: describe.
            bucket_name: TODO: describe.
            prefix: TODO: describe.
            filename: TODO: describe.
            tags: TODO: describe.
        """
        buffer.seek(0)
        file_content = buffer.read()

        # Generate S3 key
        file_key = f"{prefix}/{filename}"

        # Guess the content type
        content_type, _ = mimetypes.guess_type(filename)
        if content_type is None:
            content_type = "application/octet-stream"  # Default to binary if unknown

        # Upload file to S3
        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=file_key,
                Body=file_content,
                ContentType=content_type,
                Tagging=tags,
            )

            # NOTE: This ensures the file is downloaded correctly in the browser.
            content_disposition = f'attachment; filename="{filename}"'

            # Generate a presigned URL
            presigned_url = s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": bucket_name,
                    "Key": file_key,
                    "ResponseContentDisposition": content_disposition,
                },
                ExpiresIn=3600,  # Link expiration in seconds (1 hour)
            )
            return presigned_url
        except Exception as e:
            logging.error(f"Error uploading {filename} to S3: {e}")
            return None

    # Main logic
    async def process_files(
        *,
        excel_buffer,
        poa_buffer,
        cb_buffer,
        df_poa,
        df_cb,
        project,
        start_date,
    ):
        # Save data to buffers
        """todo

        Args:
            excel_buffer: TODO: describe.
            poa_buffer: TODO: describe.
            cb_buffer: TODO: describe.
            df_poa: TODO: describe.
            df_cb: TODO: describe.
            project: TODO: describe.
            start_date: TODO: describe.
        """
        df_poa.to_csv(poa_buffer)
        df_cb.loc[df_poa.index].to_csv(cb_buffer)

        # Define S3 and file details
        s3_client = boto3.client("s3", region_name="us-east-2")
        bucket_name = "proximal-am-documents"
        prefix = "reports"

        # File-specific details
        files = {
            "excel": {
                "buffer": excel_buffer,
                "filename": f"{project.name_short}_dc_amperage_report_{start_date.strftime('%Y-%m-%d')}_{round(time.time())}.xlsx",
            },
            "poa": {
                "buffer": poa_buffer,
                "filename": f"{project.name_short}_poa_report_{start_date.strftime('%Y-%m-%d')}_{round(time.time())}.csv",
            },
            "cb": {
                "buffer": cb_buffer,
                "filename": f"{project.name_short}_cb_report_{start_date.strftime('%Y-%m-%d')}_{round(time.time())}.csv",
            },
        }

        # Upload files and generate URLs
        presigned_urls = {}
        for key, file in files.items():
            buffer = file["buffer"]
            filename = file["filename"]
            presigned_urls[key] = upload_to_s3_and_generate_url(
                s3_client=s3_client,
                buffer=buffer,
                bucket_name=bucket_name,
                prefix=prefix,
                filename=filename,
            )

        return presigned_urls

    presigned_urls = await process_files(
        excel_buffer=excel_buffer,
        poa_buffer=poa_buffer,
        cb_buffer=cb_buffer,
        df_poa=df_poa,
        df_cb=df_cb,
        project=project,
        start_date=start_date,
    )

    logger.logger.info("Return")
    return {
        "inv": df_return_inv.to_dict(orient="split"),
        "proj": df_return_proj.to_dict(orient="split"),
        "reports": presigned_urls,
    }


@router.get("/combiner-correlation-analysis")
async def combiner_correlation_analysis(
    analysis_date: datetime.datetime | None = None,
    block_names: Annotated[list[str] | None, Query()] = None,
    project: models.Project = Depends(dependencies.get_project_api),
):
    """todo

    Args:
        analysis_date: TODO: describe.
        block_names: TODO: describe.
        project: TODO: describe.
    """

    # Initialize Lambda client
    lambda_client = boto3.client(
        "lambda",
        region_name="us-east-2",
        config=Config(
            connect_timeout=10,
            read_timeout=900,
            retries={"max_attempts": 3},
        ),
    )

    # Prepare payload
    payload = {
        "project_id": str(project.project_id),
        "analysis_date": analysis_date.strftime("%Y-%m-%d") if analysis_date else None,
        "block_names": block_names,
    }

    try:
        # Invoke Lambda function
        response = lambda_client.invoke(
            FunctionName="jigsaw-analysis-docker",
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )

        # Parse response
        response_payload = json.loads(response["Payload"].read())
        results = json.loads(response_payload["body"])
        logging.info(results)
        return results

    except Exception as e:
        logger.logger.error(f"Error invoking Lambda function: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing analysis request: {str(e)}",
        )


@router.get("/tracking-angles", response_class=ORJSONResponse)
def get_tracking_angles(
    start: datetime.datetime,
    end: datetime.datetime,
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
):
    # Convert to project timezone
    """todo

    Args:
        start: TODO: describe.
        end: TODO: describe.
        project: TODO: describe.
    """
    start = pd.to_datetime(start).tz_localize("UTC").tz_convert(project.time_zone)
    end = pd.to_datetime(end).tz_localize("UTC").tz_convert(project.time_zone)
    lon, lat = project.point.coordinates  # type: ignore
    site = utils.location.Location(lat, lon, tz=project.time_zone)

    # Get tracking angles dataframe
    df = utils.get_tracking_angles(
        site_location=site,
        start=start,
        end=end,
        freq="5min",
    )

    data = {
        "times": df.index.tolist(),
        "tracker_theta": df["tracker_theta"].tolist(),
    }

    return data
