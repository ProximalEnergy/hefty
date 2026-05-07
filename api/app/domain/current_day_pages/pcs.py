import datetime
from typing import Any

import pandas as pd
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.db_query import OutputType
from core.enumerations import DeviceTypeEnum, SensorTypeEnum, TimeInterval, TimeOffset
from fastapi import HTTPException
from natsort import natsorted
from sqlalchemy.orm import Session

from app import utils
from core import crud, models


def _normalize_timestamp(
    *,
    project: models.Project,
    value: datetime.datetime | pd.Timestamp | None,
    default_to_start_of_day: bool,
) -> pd.Timestamp:
    """Normalize a timestamp to the project's timezone and rounding rules.

    Args:
        project: Project providing the timezone context.
        value: Optional timestamp to normalize.
        default_to_start_of_day: Whether to default to start of day.
    """
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
    tag_ids: list[int],
    start: datetime.datetime,
    end: datetime.datetime,
) -> pd.DataFrame:
    """Fetch timeseries data for a list of tag IDs.

    Args:
        project_db: Database session for the project's schema.
        project: Project providing schema and timezone data.
        tag_ids: Tag IDs to query from the timeseries store.
        start: Start datetime for the query.
        end: End datetime for the query.
    """
    if len(tag_ids) == 0:
        return pd.DataFrame()

    data_timeseries_instance = DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_IDS,
        filter_values=tag_ids,
        query_start=start,
        query_end=end,
        freq=TimeInterval.FIVE_MINUTES,
        max_lookback_period=TimeOffset.FIVE_MINUTES,
        ensure_full_range=True,
        project_db=project_db,
    )
    data_timeseries = await data_timeseries_instance.get()

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
    block_tag_ids: list[int],
    pcs_tag_ids: list[int],
    pcs_module_tag_ids: list[int],
    start: datetime.datetime,
    end: datetime.datetime,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return block, PCS, and PCS module frames for the time window.

    Args:
        project_db: Database session for the project's schema.
        project: Project providing schema and timezone data.
        block_tag_ids: Tag IDs for block power data.
        pcs_tag_ids: Tag IDs for PCS power data.
        pcs_module_tag_ids: Tag IDs for PCS module data.
        start: Start datetime for the query.
        end: End datetime for the query.
    """
    df_block = await _fetch_timeseries_dataframe(
        project_db=project_db,
        project=project,
        tag_ids=block_tag_ids,
        start=start,
        end=end,
    )
    df_pcs = await _fetch_timeseries_dataframe(
        project_db=project_db,
        project=project,
        tag_ids=pcs_tag_ids,
        start=start,
        end=end,
    )
    df_pcs_module = await _fetch_timeseries_dataframe(
        project_db=project_db,
        project=project,
        tag_ids=pcs_module_tag_ids,
        start=start,
        end=end,
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
    project_schema = utils.get_project_schema(project_db=project_db)
    devices_block = await crud.project.devices.get_project_devices(
        device_type_ids=[DeviceTypeEnum.PV_BLOCK],
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    devices_block_device_id_to_name_long = dict(
        zip(
            devices_block["device_id"].astype(int),
            devices_block["name_long"].fillna(""),
        )
    )
    sorted_block_device_ids_by_name_long = natsorted(
        devices_block_device_id_to_name_long.keys(),
        key=lambda x: devices_block_device_id_to_name_long[x],
    )

    # Get block tags
    tags_block = await crud.project.tags.get_project_tags_v2(
        sensor_type_ids=[SensorTypeEnum.PV_BLOCK_AC_POWER],
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    tags_block_tag_id_to_device_id = dict(
        zip(
            tags_block["tag_id"].astype(int),
            tags_block["device_id"].astype(int),
        )
    )

    # Check if there are any block tags
    has_block_tags = not tags_block.empty

    # PCSs
    # Get PCS devices
    devices_pcs = await crud.project.devices.get_project_devices(
        device_type_ids=[DeviceTypeEnum.PV_INVERTER],
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    devices_pcs_device_id_to_name_long = dict(
        zip(
            devices_pcs["device_id"].astype(int),
            devices_pcs["name_long"].fillna(""),
        )
    )
    sorted_pcs_device_ids_by_name_long = natsorted(
        devices_pcs_device_id_to_name_long.keys(),
        key=lambda x: devices_pcs_device_id_to_name_long[x],
    )

    # Get PCS tags
    tags_pcs = await crud.project.tags.get_project_tags_v2(
        sensor_type_ids=[SensorTypeEnum.PV_INVERTER_AC_POWER],
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    tags_pcs_tag_id_to_device_id = dict(
        zip(
            tags_pcs["tag_id"].astype(int),
            tags_pcs["device_id"].astype(int),
        )
    )

    # Check if there are any PCS tags
    has_pcs_tags = not tags_pcs.empty

    # PCS MODULEs
    # Get PCS module devices
    devices_pcs_module = await crud.project.devices.get_project_devices(
        device_type_ids=[DeviceTypeEnum.PV_INVERTER_MODULE],
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    devices_pcs_module_device_id_to_name_long = dict(
        zip(
            devices_pcs_module["device_id"].astype(int),
            devices_pcs_module["name_long"].fillna(""),
        )
    )

    # Get PCS module tags
    tags_pcs_module = await crud.project.tags.get_project_tags_v2(
        sensor_type_ids=[SensorTypeEnum.PV_INVERTER_MODULE_AC_POWER],
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    tags_pcs_module_tag_id_to_device_id = dict(
        zip(
            tags_pcs_module["tag_id"].astype(int),
            tags_pcs_module["device_id"].astype(int),
        )
    )

    # Check if there are any PCS module tags
    has_pcs_module_tags = not tags_pcs_module.empty

    (
        df_block,
        df_pcs,
        df_pcs_module,
    ) = await _get_equipment_analysis_frames_async(
        project_db=project_db,
        project=project,
        block_tag_ids=(
            tags_block["tag_id"].astype(int).tolist() if has_block_tags else []
        ),
        pcs_tag_ids=(tags_pcs["tag_id"].astype(int).tolist() if has_pcs_tags else []),
        pcs_module_tag_ids=(
            tags_pcs_module["tag_id"].astype(int).tolist()
            if has_pcs_module_tags
            else []
        ),
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

        df_pcs = df_pcs.rename(
            columns=lambda tag_id: tags_pcs_tag_id_to_device_id[int(tag_id)]
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

        df_pcs_module = df_pcs_module.rename(
            columns=lambda pcs_module_device_id: tags_pcs_module_tag_id_to_device_id[
                int(pcs_module_device_id)
            ]
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
        # Filter to only include PCS device IDs that exist in df_pcs columns
        available_pcs_columns = set(df_pcs.columns.astype(int))
        block_series_list = []
        for block_device_id in block_device_id_to_pcs_device_ids:
            valid_pcs_ids = [
                pcs_id
                for pcs_id in block_device_id_to_pcs_device_ids[block_device_id]
                if pcs_id in available_pcs_columns
            ]
            if valid_pcs_ids:
                block_series_list.append(df_pcs[valid_pcs_ids].sum(axis=1))
            else:
                # If no valid PCS columns, create a series of zeros with same index
                block_series_list.append(pd.Series(0, index=df_pcs.index, dtype=float))
        df_block = pd.concat(block_series_list, axis=1)
        block_ids = list(block_device_id_to_pcs_device_ids.keys())
        df_block.columns = pd.Index(block_ids)
        df_block = df_block.fillna(0)

    return_data: dict[str, Any] = dict()

    # Block
    df_block = df_block.reindex(
        columns=sorted_block_device_ids_by_name_long, fill_value=0
    )
    generating_power_block = (df_block.T > 0).sum().values.tolist()
    max_capacity_block = (
        devices_block["capacity_ac"].max() / 1_000
        if not devices_block.empty and "capacity_ac" in devices_block.columns
        else 0
    )
    return_data["generating_power_block"] = {
        "value": generating_power_block,
        "total": len(devices_block),
    }
    return_data["block_power_distribution"] = {
        "x": [
            devices_block_device_id_to_name_long[int(block_device_id)]
            for block_device_id in df_block.columns.astype(int)
        ],
        "y": df_block.values.tolist(),
        "customdata": df_block.columns.tolist(),
        "yaxis_range_max": max_capacity_block,
    }

    norm_factor = (
        dict(
            zip(
                devices_block["device_id"].astype(int),
                devices_block["capacity_dc"].fillna(0) / 1000,
            )
        )
        if "capacity_dc" in devices_block.columns
        else {}
    )
    df_block_norm = df_block.copy()
    for col_name in df_block_norm.columns:
        if int(col_name) in norm_factor and norm_factor[int(col_name)] != 0:
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
        devices_pcs["capacity_ac"].max() / 1_000
        if not devices_pcs.empty and "capacity_ac" in devices_pcs.columns
        else 0
    )
    return_data["generating_power_pcs"] = {
        "value": generating_power_pcs,
        "total": len(devices_pcs),
    }
    return_data["pcs_power_distribution"] = {
        "x": [
            devices_pcs_device_id_to_name_long[int(pcs_device_id)]
            for pcs_device_id in df_pcs.columns.astype(int)
        ],
        "y": df_pcs.values.tolist(),
        "customdata": df_pcs.columns.tolist(),
        "yaxis_range_max": max_capacity_pcs,
    }

    norm_factor = (
        dict(
            zip(
                devices_pcs["device_id"].astype(int),
                devices_pcs["capacity_dc"].fillna(0) / 1000,
            )
        )
        if "capacity_dc" in devices_pcs.columns
        else {}
    )
    df_pcs_norm = df_pcs.copy()
    for col_name in df_pcs_norm.columns:
        if int(col_name) in norm_factor and norm_factor[int(col_name)] != 0:
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
            devices_pcs_module["capacity_ac"].max() / 1_000
            if not devices_pcs_module.empty
            and "capacity_ac" in devices_pcs_module.columns
            else 0
        )
        return_data["generating_power_pcs_module"] = {
            "value": generating_power_pcs_module,
            "total": len(devices_pcs_module),
        }
        return_data["pcs_module_power_distribution"] = {
            "x": [
                devices_pcs_module_device_id_to_name_long[int(pcs_module_device_id)]
                for pcs_module_device_id in df_pcs_module.columns.astype(int)
            ],
            "y": (df_pcs_module.values.tolist()),
            "customdata": df_pcs_module.columns.tolist(),
            "yaxis_range_max": max_capacity_pcs_module,
        }

        norm_factor = (
            dict(
                zip(
                    devices_pcs_module["device_id"].astype(int),
                    devices_pcs_module["capacity_ac"].fillna(0) / 1000,
                )
            )
            if "capacity_ac" in devices_pcs_module.columns
            else {}
        )
        df_pcs_module_norm = df_pcs_module.copy()
        for col_name in df_pcs_module_norm.columns:
            if int(col_name) in norm_factor and norm_factor[int(col_name)] != 0:
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
        (
            devices_block["capacity_ac"].sum() / 1000
            if not devices_block.empty and "capacity_ac" in devices_block.columns
            else 0
        ),
        0,
    )

    return_data["total_power_output"] = {
        "value": total_power,
        "total_nameplate": total_nameplate,
    }

    timestamps_index = df_pcs.index.tz_convert(project.time_zone)  # type: ignore
    return_data["timestamps"] = timestamps_index.tolist()

    return return_data
