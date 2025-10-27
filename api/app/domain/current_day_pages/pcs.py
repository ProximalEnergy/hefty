import datetime
from typing import Any

import pandas as pd
from fastapi import HTTPException
from natsort import natsorted
from sqlalchemy.orm import Session

import core
from app import utils
from core import models


def get_equipment_analysis_pcs_data(
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
    if end is not None and end > pd.Timestamp.utcnow():
        end = pd.Timestamp.utcnow().floor("5min")

    live = False
    if not start and not end:
        live = True
        end = pd.Timestamp.utcnow().floor("5min")
        start = end - pd.Timedelta(minutes=30)

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

    # Initialize DataFrames
    df_block = pd.DataFrame()
    df_pcs = pd.DataFrame()
    df_pcs_module = pd.DataFrame()

    # Get data for block tags
    if has_block_tags:
        df_block = utils.data_df(
            project_db,
            project,
            tags_block,
            start=start,
            end=end,
            fillna_zero=False,
        )
        if live:
            df_block = df_block.dropna(how="all")
            if df_block.empty:
                raise HTTPException(status_code=404, detail="No data found")
            else:
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

    # Get data for PCS tags
    if has_pcs_tags:
        df_pcs = utils.data_df(
            project_db,
            project,
            tags_pcs,
            start=start,
            end=end,
            fillna_zero=False,
        )
        if live:
            df_pcs = df_pcs.dropna(how="all")
            if df_pcs.empty:
                raise HTTPException(status_code=404, detail="No data found")
            else:
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

    # Get data for PCS module tags
    if has_pcs_module_tags:
        df_pcs_module = utils.data_df(
            project_db,
            project,
            tags_pcs_module,
            start=start,
            end=end,
            fillna_zero=False,
        )
        if live:
            df_pcs_module = df_pcs_module.dropna(how="all")
            if df_pcs_module.empty:
                raise HTTPException(status_code=404, detail="No data found")
            else:
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
        df_block.columns = pd.Index(list(block_device_id_to_pcs_device_ids.keys()))  # type: ignore
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

    return_data["timestamps"] = df_pcs.index.tz_convert(project.time_zone).tolist()  # type: ignore

    return return_data
