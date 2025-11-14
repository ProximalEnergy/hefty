import datetime
from typing import Any

import pandas as pd
from fastapi import HTTPException
from natsort import natsorted
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import utils
from core import models
from core.dependencies import get_db_session_async
from core.enumerations import TimeInterval, TimeOffset


def _normalize_timestamp(
    *,
    project: models.Project,
    value: datetime.datetime | pd.Timestamp | None,
    default_to_start_of_day: bool,
) -> pd.Timestamp:
    if value is None:
        if default_to_start_of_day:
            normalized = pd.Timestamp.now(tz=project.time_zone).floor("D")
        else:
            normalized = pd.Timestamp.now(tz=project.time_zone).ceil("5min")
    else:
        normalized = pd.Timestamp(value)
        if normalized.tzinfo is None:
            normalized = normalized.tz_localize(project.time_zone)
        else:
            normalized = normalized.tz_convert(project.time_zone)

    return normalized


async def _fetch_timeseries_dataframe(
    *,
    project_db: Session,
    project: models.Project,
    tags: list[models.Tag],
    start: datetime.datetime,
    end: datetime.datetime,
    operational_db: AsyncSession,
) -> pd.DataFrame:
    if len(tags) == 0:
        return pd.DataFrame()

    data_timeseries = await core.crud.project.data_timeseries.DataTimeseries.get(
        project_name_short=project.name_short,
        tag_ids=[tag.tag_id for tag in tags],
        query_start=start,
        query_end=end,
        agg_interval=TimeInterval.FIVE_MINUTES,
        max_lookback_period=TimeOffset.FIVE_MINUTES,
        ensure_full_range=True,
        project_db=project_db,
        operational_db=operational_db,
        return_arrow=False,
    )

    df_polars = data_timeseries.df
    if df_polars.height == 0:
        return pd.DataFrame()

    df = df_polars.to_pandas()
    time_col = "time" if "time" in df.columns else "time_bucket"
    if time_col not in df.columns:
        return pd.DataFrame()

    df = df.set_index(time_col, drop=True)
    remaining_time_cols = {
        column for column in ("time", "time_bucket") if column in df.columns
    }
    if remaining_time_cols:
        df = df.drop(columns=list(remaining_time_cols))

    if len(df.index) == 0:
        df.index = pd.DatetimeIndex([], tz=project.time_zone)
    else:
        datetime_index = pd.DatetimeIndex(df.index)
        if datetime_index.tz is None:
            datetime_index = datetime_index.tz_localize(project.time_zone)
        else:
            datetime_index = datetime_index.tz_convert(project.time_zone)
        df.index = datetime_index

    df = df.sort_index()
    df.columns = df.columns.astype(int)

    return df


async def _get_equipment_analysis_frames_async(
    *,
    project_db: Session,
    project: models.Project,
    block_tags: list[models.Tag],
    pcs_tags: list[models.Tag],
    pcs_module_tags: list[models.Tag],
    start: datetime.datetime,
    end: datetime.datetime,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    async with get_db_session_async(schema=None) as operational_db:
        df_block = await _fetch_timeseries_dataframe(
            project_db=project_db,
            project=project,
            tags=block_tags,
            start=start,
            end=end,
            operational_db=operational_db,
        )
        df_pcs = await _fetch_timeseries_dataframe(
            project_db=project_db,
            project=project,
            tags=pcs_tags,
            start=start,
            end=end,
            operational_db=operational_db,
        )
        df_pcs_module = await _fetch_timeseries_dataframe(
            project_db=project_db,
            project=project,
            tags=pcs_module_tags,
            start=start,
            end=end,
            operational_db=operational_db,
        )

    return df_block, df_pcs, df_pcs_module


async def get_equipment_analysis_pcs_data(
    *,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    project_db: Session,
    project: models.Project,
) -> dict[str, Any]:
    """
    Get PCS equipment analysis data for a project.

    Args:
        start: Start datetime for data retrieval
        end: End datetime for data retrieval
        project_db: Database session for the project
        project: Project model instance

    Returns:
        Dictionary containing equipment analysis data
    """
    live = start is None and end is None

    if live:
        end_ts = pd.Timestamp.now(tz=project.time_zone).floor("5min")
        start_ts = end_ts - pd.Timedelta(minutes=30)
    else:
        start_ts = _normalize_timestamp(
            project=project,
            value=start,
            default_to_start_of_day=True,
        )
        end_ts = _normalize_timestamp(
            project=project,
            value=end,
            default_to_start_of_day=False,
        )
        now_project = pd.Timestamp.now(tz=project.time_zone).floor("5min")
        if end_ts > now_project:
            end_ts = now_project

    # BLOCKs
    # Get block devices
    devices_block = core.crud.project.devices.get_project_devices(
        project_db,
        device_type_ids=[6],
    ).models()
    devices_block_device_id_to_name_long = {
        device.device_id: device.name_long for device in devices_block
    }
    sorted_block_device_ids_by_name_long = natsorted(
        devices_block_device_id_to_name_long.keys(),
        key=lambda x: devices_block_device_id_to_name_long[x],
    )

    # Get block tags
    tags_block = core.crud.project.tags.get_project_tags(
        project_db,
        sensor_type_name_shorts=["block_ac_power"],
    ).models()
    tags_block_tag_id_to_device_id = {tag.tag_id: tag.device_id for tag in tags_block}

    # Check if there are any block tags
    has_block_tags = len(tags_block) > 0

    # PCSs
    # Get PCS devices
    devices_pcs = core.crud.project.devices.get_project_devices(
        project_db,
        device_type_ids=[2],
    ).models()
    devices_pcs_device_id_to_name_long = {
        device.device_id: device.name_long for device in devices_pcs
    }
    sorted_pcs_device_ids_by_name_long = natsorted(
        devices_pcs_device_id_to_name_long.keys(),
        key=lambda x: devices_pcs_device_id_to_name_long[x],
    )

    # Get PCS tags
    tags_pcs = core.crud.project.tags.get_project_tags(
        project_db,
        sensor_type_name_shorts=["pv_pcs_ac_power"],
    ).models()
    tags_pcs_tag_id_to_device_id = {tag.tag_id: tag.device_id for tag in tags_pcs}

    # Check if there are any PCS tags
    has_pcs_tags = len(tags_pcs) > 0

    # PCS MODULEs
    # Get PCS module devices
    devices_pcs_module = core.crud.project.devices.get_project_devices(
        project_db,
        device_type_ids=[3],
    ).models()
    devices_pcs_module_device_id_to_name_long = {
        device.device_id: device.name_long for device in devices_pcs_module
    }

    # Get PCS module tags
    tags_pcs_module = core.crud.project.tags.get_project_tags(
        project_db,
        sensor_type_name_shorts=["pv_pcs_module_ac_power"],
    ).models()
    tags_pcs_module_tag_id_to_device_id = {
        tag.tag_id: tag.device_id for tag in tags_pcs_module
    }

    # Check if there are any PCS module tags
    has_pcs_module_tags = len(tags_pcs_module) > 0

    (
        df_block,
        df_pcs,
        df_pcs_module,
    ) = await _get_equipment_analysis_frames_async(
        project_db=project_db,
        project=project,
        block_tags=tags_block if has_block_tags else [],
        pcs_tags=tags_pcs if has_pcs_tags else [],
        pcs_module_tags=tags_pcs_module if has_pcs_module_tags else [],
        start=start_ts.to_pydatetime(),
        end=end_ts.to_pydatetime(),
    )

    if has_block_tags:
        if live:
            df_block = df_block.dropna(how="all")
            if df_block.empty:
                raise HTTPException(status_code=404, detail="No data found")
            df_block = df_block.tail(1)

        df_block.columns = pd.Index(
            [
                tags_block_tag_id_to_device_id[int(block_device_id)]
                for block_device_id in df_block.columns
            ],
        ).astype(int)
        df_block = df_block[sorted(df_block.columns)]
        df_block = df_block.fillna(0)
    else:
        df_block = pd.DataFrame()

    if has_pcs_tags:
        if live:
            df_pcs = df_pcs.dropna(how="all")
            if df_pcs.empty:
                raise HTTPException(status_code=404, detail="No data found")
            df_pcs = df_pcs.tail(1)

        df_pcs.columns = pd.Index(
            [
                tags_pcs_tag_id_to_device_id[tag_id]
                for tag_id in df_pcs.columns.astype(int)
            ],
        )
        df_pcs = df_pcs[sorted(df_pcs.columns)]
        df_pcs = df_pcs.fillna(0)
    else:
        df_pcs = pd.DataFrame()

    if has_pcs_module_tags:
        if live:
            df_pcs_module = df_pcs_module.dropna(how="all")
            if df_pcs_module.empty:
                raise HTTPException(status_code=404, detail="No data found")
            df_pcs_module = df_pcs_module.tail(1)

        df_pcs_module.columns = pd.Index(
            [
                tags_pcs_module_tag_id_to_device_id[pcs_module_device_id]
                for pcs_module_device_id in df_pcs_module.columns.astype(int)
            ],
        )
        df_pcs_module = df_pcs_module[sorted(df_pcs_module.columns)]
        df_pcs_module = df_pcs_module.fillna(0)
    else:
        df_pcs_module = pd.DataFrame()

    # If there are not block tags, sum PCS data to get block data
    if not has_block_tags:
        block_device_id_to_pcs_device_ids = utils.map_ancestors_to_descendents(
            ancestors=devices_block,
            descendents=devices_pcs,
        )
        df_block = pd.concat(
            [
                df_pcs[block_device_id_to_pcs_device_ids[block_device_id]].sum(axis=1)
                for block_device_id in block_device_id_to_pcs_device_ids
            ],
            axis=1,
        )
        block_ids = list(block_device_id_to_pcs_device_ids.keys())
        df_block.columns = pd.Index(block_ids)  # type: ignore
        df_block = df_block.fillna(0)

    return_data: dict[str, Any] = dict()

    # Block
    df_block = df_block.reindex(columns=sorted_block_device_ids_by_name_long)
    generating_power_block = (df_block.T > 0).sum().values.tolist()
    max_capacity_block = (
        max(
            [
                device.capacity_ac
                for device in devices_block
                if device.capacity_ac is not None
            ]
        )
        / 1_000
    )
    return_data["generating_power_block"] = {
        "value": generating_power_block,
        "total": len(devices_block),
    }
    return_data["block_power_distribution"] = {
        "x": [
            devices_block_device_id_to_name_long[block_device_id]
            for block_device_id in df_block.columns.astype(int)
        ],
        "y": df_block.values.tolist(),
        "customdata": df_block.columns.tolist(),
        "yaxis_range_max": max_capacity_block,
    }

    norm_factor = {
        x: y
        for x, y in zip(
            [device.device_id for device in devices_block],
            [
                device.capacity_dc / 1000
                for device in devices_block
                if device.capacity_dc is not None
            ],
        )
    }
    df_block_norm = df_block.copy()
    for col_name in df_block_norm.columns:
        if int(col_name) in norm_factor:
            df_block_norm[col_name] = (
                df_block_norm[col_name] / norm_factor[int(col_name)]
            )

    return_data["block_power_distribution_norm"] = {
        "x": [
            devices_block_device_id_to_name_long[int(block_device_id)]
            for block_device_id in df_block_norm.columns
        ],
        "y": (df_block_norm.values.tolist()),
        "customdata": df_block_norm.columns.tolist(),
        "yaxis_range_max": 1,
    }

    # PCS
    df_pcs = df_pcs[sorted_pcs_device_ids_by_name_long]
    generating_power_pcs = (df_pcs.T > 0).sum().values.tolist()
    max_capacity_pcs = (
        max(
            [
                device.capacity_ac
                for device in devices_pcs
                if device.capacity_ac is not None
            ]
        )
        / 1_000
    )
    return_data["generating_power_pcs"] = {
        "value": generating_power_pcs,
        "total": len(devices_pcs),
    }
    return_data["pcs_power_distribution"] = {
        "x": [
            devices_pcs_device_id_to_name_long[pcs_device_id]
            for pcs_device_id in df_pcs.columns.astype(int)
        ],
        "y": df_pcs.values.tolist(),
        "customdata": df_pcs.columns.tolist(),
        "yaxis_range_max": max_capacity_pcs,
    }

    norm_factor = {
        x: y
        for x, y in zip(
            [device.device_id for device in devices_pcs],
            [
                device.capacity_dc / 1000
                for device in devices_pcs
                if device.capacity_dc is not None
            ],
        )
    }
    df_pcs_norm = df_pcs.copy()
    for col_name in df_pcs_norm.columns:
        if int(col_name) in norm_factor:
            df_pcs_norm[col_name] = df_pcs_norm[col_name] / norm_factor[int(col_name)]

    return_data["pcs_power_distribution_norm"] = {
        "x": [
            devices_pcs_device_id_to_name_long[int(pcs_device_id)]
            for pcs_device_id in df_pcs_norm.columns
        ],
        "y": (df_pcs_norm.values.tolist()),
        "customdata": df_pcs_norm.columns.tolist(),
        "yaxis_range_max": 1,
    }

    # PCS Module
    if has_pcs_module_tags:
        generating_power_pcs_module = (df_pcs_module.T > 0).sum().values.tolist()
        max_capacity_pcs_module = (
            max(
                [
                    device.capacity_ac
                    for device in devices_pcs_module
                    if device.capacity_ac is not None
                ]
            )
            / 1_000
        )
        return_data["generating_power_pcs_module"] = {
            "value": generating_power_pcs_module,
            "total": len(devices_pcs_module),
        }
        return_data["pcs_module_power_distribution"] = {
            "x": [
                devices_pcs_module_device_id_to_name_long[pcs_module_device_id]
                for pcs_module_device_id in df_pcs_module.columns.astype(int)
            ],
            "y": (df_pcs_module.values.tolist()),
            "customdata": df_pcs_module.columns.tolist(),
            "yaxis_range_max": max_capacity_pcs_module,
        }

        norm_factor = {
            x: y
            for x, y in zip(
                [device.device_id for device in devices_pcs_module],
                [
                    device.capacity_ac / 1000
                    for device in devices_pcs_module
                    if device.capacity_ac is not None
                ],
            )
        }
        df_pcs_module_norm = df_pcs_module.copy()
        for col_name in df_pcs_module_norm.columns:
            if int(col_name) in norm_factor:
                df_pcs_module_norm[col_name] = (
                    df_pcs_module_norm[col_name] / norm_factor[int(col_name)]
                )

        return_data["pcs_module_power_distribution_norm"] = {
            "x": [
                devices_pcs_module_device_id_to_name_long[int(pcs_module_device_id)]
                for pcs_module_device_id in df_pcs_module_norm.columns
            ],
            "y": (df_pcs_module_norm.values.tolist()),
            "customdata": df_pcs_module_norm.columns.tolist(),
            "yaxis_range_max": 1,
        }

    total_power = df_block.sum(axis=1).round(0).values.tolist()
    total_nameplate = round(
        sum(
            [
                device.capacity_ac
                for device in devices_block
                if device.capacity_ac is not None
            ]
        )
        / 1_000,
        0,
    )

    return_data["total_power_output"] = {
        "value": total_power,
        "total_nameplate": total_nameplate,
    }

    timestamps_index = df_pcs.index.tz_convert(project.time_zone)  # type: ignore
    return_data["timestamps"] = timestamps_index.tolist()

    return return_data
