import datetime
from typing import Annotated

import pandas as pd
import polars as pl
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.crud.project.events import get_project_events
from core.db_query import OutputType
from core.enumerations import DeviceType, SensorType
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import ORJSONResponse
from natsort import natsorted
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import dependencies, utils
from app.domain.current_day_pages.bess import get_bess_data
from app.domain.current_day_pages.bess_pcs import get_bess_pcs_data
from app.domain.current_day_pages.combiner import get_equipment_analysis_combiner_data
from app.domain.current_day_pages.pcs import get_equipment_analysis_pcs_data
from app.domain.current_day_pages.tracker import (
    get_tracker_by_pv_block_id_data,
    get_tracker_data,
)
from core import models

router = APIRouter(
    prefix="/equipment-analysis",
    tags=["equipment-analysis"],
    include_in_schema=utils.get_include_in_schema(),
)


@router.get(
    "/bess",
    response_class=ORJSONResponse,
)
async def get_bess(
    start: datetime.datetime,
    end: datetime.datetime,
    project: models.Project = Depends(dependencies.get_project_api),
    project_db: Session = Depends(dependencies.get_project_db),
):
    """todo

    Args:
        project_id: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        project: TODO: describe.
        project_db: TODO: describe.
    """
    return await get_bess_data(
        project=project,
        project_db=project_db,
        start=start,
        end=end,
    )


@router.get(
    "/bess-pcs",
    response_class=ORJSONResponse,
)
async def get_bess_pcs(
    start: datetime.datetime,
    end: datetime.datetime,
    project: models.Project = Depends(dependencies.get_project_api),
    project_db: Session = Depends(dependencies.get_project_db),
):
    """todo

    Args:
        start: TODO: describe.
        end: TODO: describe.
        project: TODO: describe.
        project_db: TODO: describe.
    """
    return await get_bess_pcs_data(
        project=project,
        project_db=project_db,
        start=start,
        end=end,
    )


@router.get(
    "/combiner",
    response_class=ORJSONResponse,
    deprecated=True,
)
async def get_equipment_analysis_combiner(
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
):
    """todo

    Args:
        project_db: TODO: describe.
        project: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
    """
    return await get_equipment_analysis_combiner_data(
        project_db=project_db,
        project=project,
        start=start,
        end=end,
    )


@router.get(
    "/tracker",
    response_class=ORJSONResponse,
)
async def get_tracker(
    start: datetime.date,
    end: datetime.date,
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
):
    """todo

    Args:
        start: TODO: describe.
        end: TODO: describe.
        project_db: TODO: describe.
        project: TODO: describe.
    """
    return await get_tracker_data(
        start=start,
        end=end,
        project_db=project_db,
        project=project,
    )


@router.get(
    "/tracker/{pv_block_id}",
    response_class=ORJSONResponse,
)
async def get_tracker_by_pv_block_id(
    pv_block_id: int,
    start: datetime.datetime,
    end: datetime.datetime,
    project: models.Project = Depends(dependencies.get_project_api),
    project_db: Session = Depends(dependencies.get_project_db),
):
    """todo

    Args:
        pv_block_id: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        project: TODO: describe.
        project_db: TODO: describe.
    """
    return await get_tracker_by_pv_block_id_data(
        pv_block_id=pv_block_id,
        project=project,
        project_db=project_db,
        start=start,
        end=end,
    )


@router.get("/pcs", response_class=ORJSONResponse)
async def get_equipment_analysis_pcs(
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    project_db: Session = Depends(dependencies.get_project_db),
    project: models.Project = Depends(dependencies.get_project_api),
):
    """todo

    Args:
        start: TODO: describe.
        end: TODO: describe.
        project_db: TODO: describe.
        project: TODO: describe.
    """
    return await get_equipment_analysis_pcs_data(
        start=start,
        end=end,
        project_db=project_db,
        project=project,
    )


@router.get("/heatmap/{sensor_type_name_short}", response_class=ORJSONResponse)
async def get_heatmap(
    sensor_type_name_short: str,
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
):
    """todo

    Args:
        sensor_type_name_short: TODO: describe.
        project_db: TODO: describe.
        project: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        agg: TODO: describe.
        fillna_zero: TODO: describe.
    """
    project_schema = utils.get_project_schema(project_db=project_db)
    tags_query = core.crud.project.tags.get_project_tags_v2(
        sensor_type_name_shorts=[sensor_type_name_short],
        deep=False,
    )
    tags_df = await tags_query.get_async(
        output_type=OutputType.POLARS,
        schema=project_schema,
    )

    if tags_df.is_empty():
        fallback_query = core.crud.project.tags.get_project_tags_v2(
            sensor_type_ids=[SensorType.PV_PCS_MODULE_AC_POWER],
            deep=False,
        )
        tags_df = await fallback_query.get_async(
            output_type=OutputType.POLARS,
            schema=project_schema,
        )

    if tags_df.is_empty():
        raise HTTPException(status_code=404, detail="No tags found")

    if start is None:
        start = pd.Timestamp.utcnow().floor("5min") - pd.DateOffset(days=1)
    if end is None:
        end = pd.Timestamp.utcnow().floor("5min")

    data_timeseries_instance = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_POLARS,
        filter_values=tags_df,
        query_start=start,
        query_end=end,
        project_db=project_db,
    ).get()

    df = data_timeseries_instance.df.to_pandas()
    df = df.set_index("time")
    df.index = pd.to_datetime(df.index).tz_convert(project.time_zone)
    df.columns = df.columns.astype(int)

    device_ids = [
        int(device_id) for device_id in tags_df["device_id"].drop_nulls().to_list()
    ]
    devices_df = await core.crud.project.devices.get_project_devices(
        device_ids=device_ids,
    ).get_async(output_type=OutputType.POLARS, schema=project_schema)

    device_id_to_name_long = dict(
        zip(
            devices_df["device_id"].cast(pl.Int64).to_list(),
            devices_df["name_long"].fill_null("").to_list(),
        )
    )
    tag_ids = tags_df["tag_id"].to_list()
    tag_device_ids = tags_df["device_id"].to_list()
    tag_id_to_device_name_long = {
        tag_id: device_id_to_name_long.get(tag_device_id, "")
        for tag_id, tag_device_id in zip(tag_ids, tag_device_ids, strict=True)
    }

    columns = df.columns.astype(int).tolist()
    columns = [tag_id_to_device_name_long.get(tag_id, tag_id) for tag_id in columns]
    df.columns = pd.Index(columns)
    df = df[natsorted(df.columns)]

    timestamps = df.index.tz_convert(project.time_zone).tolist()  # type: ignore
    columns = df.columns.tolist()
    values = df.T.values.tolist()

    return {
        "x": timestamps,
        "y": columns,
        "z": values,
    }


@router.get("/sunburst-data")
async def get_sunburst_data(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project_id,
    mode: str = "events",
    ignored_device_type_ids: list[int] = [4, 5, 7, 10, 19, 20, 29, 30],
):
    """todo

    Args:
        db: TODO: describe.
        project_db: TODO: describe.
        project_id: TODO: describe.
        mode: TODO: describe.
        ignored_device_type_ids: TODO: describe.
    """
    project_schema = utils.get_project_schema(project_db=project_db)
    devices_query = core.crud.project.devices.get_project_devices()
    devices_df = await devices_query.get_async(
        output_type=OutputType.PANDAS,
        schema=project_schema,
    )
    devices_df = devices_df.copy()
    devices_df["device_id"] = devices_df["device_id"].astype(int)
    devices_df["device_type_id"] = devices_df["device_type_id"].astype(int)
    devices_df["parent_device_id"] = devices_df["parent_device_id"].where(
        pd.notna(devices_df["parent_device_id"]), None
    )
    devices = devices_df.to_dict("records")

    if len(devices) == 0:
        raise HTTPException(status_code=404, detail="No devices found")

    device_map = {device["device_id"]: device for device in devices}

    # Reassign children of ignored devices
    for device in devices:
        current_parent_id = device.get("parent_device_id")
        if pd.isna(current_parent_id):
            current_parent_id = None
        while current_parent_id:
            parent_device = device_map.get(int(current_parent_id))
            if (
                not parent_device
                or parent_device["device_type_id"] not in ignored_device_type_ids
            ):
                break
            current_parent_id = parent_device.get("parent_device_id")
            if pd.isna(current_parent_id):
                current_parent_id = None
        device["parent_device_id"] = current_parent_id

    # Filter devices again to remove ignored devices after re-parenting
    devices = [
        device
        for device in devices
        if device["device_type_id"] not in ignored_device_type_ids
    ]
    devices = natsorted(
        devices,
        key=lambda x: (x["device_type_id"], x.get("name_long") or ""),
    )

    # Build hierarchy
    hierarchy: dict[int, list[int]] = {}
    for device in devices:
        parent_device_id = device.get("parent_device_id")
        if pd.isna(parent_device_id):
            parent_device_id = None
        if parent_device_id is not None:
            parent = int(parent_device_id)
            if parent in hierarchy:
                hierarchy[parent].append(device["device_id"])
            else:
                hierarchy[parent] = [device["device_id"]]

    ## Serrano hotfix
    ## TODO: figure out why the Ghost device is in the hierarchy in the first place
    if 0 in hierarchy.keys():
        hierarchy.pop(0)

    device_types = await core.crud.operational.device_types.get_device_types(db=db)
    device_names = {}
    for device in devices:
        device_id = device["device_id"]
        device_type = [
            x for x in device_types if x.device_type_id == device["device_type_id"]
        ][0]
        name_long = device.get("name_long")
        if pd.isna(name_long):
            name_long = None
        if name_long is not None:
            device_names[device_id] = f"{device_type.name_long} {name_long}"
        else:
            device_names[device_id] = str(device_type.name_long)

    labels = []
    parents = []
    colors = []
    project_device = [
        device["device_id"]
        for device in devices
        if device["device_type_id"] == DeviceType.PROJECT
    ][0]

    if mode == "events":
        project_name_short = dependencies.get_project_name_short(project_id=project_id)
        if not project_name_short:
            raise HTTPException(status_code=404, detail="Project not found")

        online_status_dict = {x["device_id"]: 0 for x in devices}
        events_query = get_project_events(
            open=True,
        )
        events_df = await events_query.get_async(schema=project_name_short)
        if events_df is not None and not events_df.is_empty():
            for event in events_df.to_dicts():
                online_status_dict[int(event["device_id"])] = 2

        for parent, children in hierarchy.items():
            all_online = True
            all_offline = True
            for child in children:
                if online_status_dict[child] == 0:
                    all_offline = False
                elif online_status_dict[child] == 2:
                    all_online = False
            if not all_online and not all_offline and online_status_dict[parent] == 0:
                online_status_dict[parent] = 1

        def update_parents(*, device, hierarchy):
            # Find the parent of the current device
            """todo

            Args:
                device: TODO: describe.
                hierarchy: TODO: describe.
            """
            if device["parent_device_id"]:
                parent_device = [
                    x for x in devices if x["device_id"] == device["parent_device_id"]
                ][0]
                if online_status_dict[parent_device["device_id"]] == 0:
                    online_status_dict[parent_device["device_id"]] = 1
                    # Recursively update the parent device
                    update_parents(device=parent_device, hierarchy=hierarchy)

        for device in devices:
            if online_status_dict[device["device_id"]] in [1, 2]:
                update_parents(device=device, hierarchy=hierarchy)

        labels.append(device_names[project_device])
        parents.append("")
        if (1 in [online_status_dict[x] for x in hierarchy[project_device]]) or (
            2 in [online_status_dict[x] for x in hierarchy[project_device]]
        ):
            colors.append("orange")
        else:
            colors.append("green")

        for parent, children in hierarchy.items():
            for child in children:
                labels.append(device_names[child])
                parents.append(device_names[parent])
                if online_status_dict[child] == 0:
                    colors.append("green")
                elif online_status_dict[child] == 1:
                    colors.append("orange")
                elif online_status_dict[child] == 2:
                    colors.append("red")

    device_names_reversed = {x: y for y, x in device_names.items()}
    return {
        "labels": labels,
        "parents": parents,
        "colors": colors,
        "device_names": device_names_reversed,
        "hierarchy": hierarchy,
    }
