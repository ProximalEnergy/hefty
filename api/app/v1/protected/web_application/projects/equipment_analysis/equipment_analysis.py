import datetime
from typing import Annotated

import pandas as pd
from core.crud.project.events import get_project_events
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
def get_bess(
    project_id,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
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
    return get_bess_data(
        project=project,
        project_db=project_db,
        start=start,
        end=end,
    )


@router.get(
    "/bess-pcs",
    response_class=ORJSONResponse,
)
def get_bess_pcs(
    project_id,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
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
    return get_bess_pcs_data(
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
def get_equipment_analysis_combiner(
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
    return get_equipment_analysis_combiner_data(
        project_db=project_db,
        project=project,
        start=start,
        end=end,
    )


@router.get(
    "/tracker",
    response_class=ORJSONResponse,
)
def get_tracker(
    start: datetime.date,
    end: datetime.date,
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    project_id,
):
    """todo

    Args:
        start: TODO: describe.
        end: TODO: describe.
        project_db: TODO: describe.
        project: TODO: describe.
        project_id: TODO: describe.
    """
    return get_tracker_data(
        start=start,
        end=end,
        project_db=project_db,
        project=project,
    )


@router.get(
    "/tracker/{pv_block_id}",
    response_class=ORJSONResponse,
)
def get_tracker_by_pv_block_id(
    pv_block_id: int,
    project_id,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    project: models.Project = Depends(dependencies.get_project_api),
    project_db: Session = Depends(dependencies.get_project_db),
):
    """todo

    Args:
        pv_block_id: TODO: describe.
        project_id: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        project: TODO: describe.
        project_db: TODO: describe.
    """
    return get_tracker_by_pv_block_id_data(
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
def get_heatmap(
    *,
    sensor_type_name_short: str,
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    agg: str = "instantaneous",
    fillna_zero: bool = True,
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
    devices = core.crud.project.devices.get_project_devices(project_db).models()

    if len(devices) == 0:
        raise HTTPException(status_code=404, detail="No devices found")

    device_map = {device.device_id: device for device in devices}

    # Reassign children of ignored devices
    for device in devices:
        current_parent_id = device.parent_device_id
        while current_parent_id:
            parent_device = device_map.get(current_parent_id)
            if (
                not parent_device
                or parent_device.device_type_id not in ignored_device_type_ids
            ):
                break
            current_parent_id = parent_device.parent_device_id
        device.parent_device_id = current_parent_id

    # Filter devices again to remove ignored devices after re-parenting
    devices = [x for x in devices if x.device_type_id not in ignored_device_type_ids]
    devices = natsorted(devices, key=lambda x: (x.device_type_id, x.name_long or ""))

    # Build hierarchy
    hierarchy: dict[int, list[int]] = {}
    for device in devices:
        if device.parent_device_id is not None:
            parent = int(device.parent_device_id)
            if parent in hierarchy.keys():
                hierarchy[parent].append(device.device_id)
            else:
                hierarchy[parent] = [device.device_id]

    ## Serrano hotfix
    ## TODO: figure out why the Ghost device is in the hierarchy in the first place
    if 0 in hierarchy.keys():
        hierarchy.pop(0)

    device_types = await core.crud.operational.device_types.get_device_types(db=db)
    device_names = {}
    for device in devices:
        device_id = device.device_id
        device_type = [
            x for x in device_types if x.device_type_id == device.device_type_id
        ][0]
        if device.name_long is not None:
            device_names[device_id] = (
                str(device_type.name_long) + " " + str(device.name_long)
            )
        else:
            device_names[device_id] = str(device_type.name_long)

    labels = []
    parents = []
    colors = []
    project_device = [
        x.device_id for x in devices if x.device_type_id == DeviceType.PROJECT
    ][0]

    if mode == "events":
        project_name_short = dependencies.get_project_name_short(project_id=project_id)
        if not project_name_short:
            raise HTTPException(status_code=404, detail="Project not found")

        online_status_dict = {x.device_id: 0 for x in devices}
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
            if device.parent_device_id:
                parent_device = [
                    x for x in devices if x.device_id == device.parent_device_id
                ][0]
                if online_status_dict[parent_device.device_id] == 0:
                    online_status_dict[parent_device.device_id] = 1
                    # Recursively update the parent device
                    update_parents(device=parent_device, hierarchy=hierarchy)

        for device in devices:
            if online_status_dict[device.device_id] in [1, 2]:
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
