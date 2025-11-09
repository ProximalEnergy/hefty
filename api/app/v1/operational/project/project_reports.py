import datetime
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import interfaces
from app._crud.operational.cec_pv_inverters import get_cec_pv_inverters
from app.dependencies import get_async_db, get_project_api, get_project_db
from app.utils import data_df
from core import models

router = APIRouter(prefix="/projects/{project_id}/reports", tags=["project_reports"])


@router.get("/", response_model=interfaces.Report)
def get_project_reports():
    pass


@router.get("/pcs-apparent-vs-voltage")
async def get_pcs_apparent_vs_voltage(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    project_db: Annotated[Session, Depends(get_project_db)],
    project: Annotated[models.Project, Depends(get_project_api)],
    start: datetime.datetime,
    end: datetime.datetime,
):
    tags = core.crud.project.tags.get_project_tags(
        project_db, sensor_type_ids=[132, 133, 134, 135]
    ).models()
    tags_df = pd.DataFrame.from_records([tag.__dict__ for tag in tags]).set_index(
        "tag_id"
    )
    if "_sa_instance_state" in tags_df.columns:
        tags_df = tags_df.drop(columns=["_sa_instance_state"])
    df = data_df(project_db, project, tags=tags, start=start, end=end)
    df.index = pd.to_datetime(df.index).tz_convert(None).tz_localize(project.time_zone)

    apparent_idx = tags_df[tags_df["sensor_type_id"] == 132].index.tolist()
    df_apparent = df.loc[:, apparent_idx]
    df_apparent = df_apparent.rename(columns=tags_df.loc[apparent_idx, "device_id"])  # type: ignore

    vab_idx = tags_df[tags_df["sensor_type_id"] == 133].index.tolist()
    vbc_idx = tags_df[tags_df["sensor_type_id"] == 134].index.tolist()
    vca_idx = tags_df[tags_df["sensor_type_id"] == 135].index.tolist()
    voltage_items = (
        tags_df.loc[vab_idx + vbc_idx + vca_idx]  # type: ignore
        .groupby("device_id", group_keys=False)  # type: ignore
        .apply(lambda x: x.index.tolist(), include_groups=False)  # type: ignore
        .to_dict()
    )
    df_voltage = pd.DataFrame(columns=voltage_items.keys(), index=df.index)
    for device_id, tag_ids in voltage_items.items():
        df_voltage.loc[:, device_id] = df.loc[:, tag_ids].mean(axis=1)

    devices = core.crud.project.devices.get_project_devices(
        project_db, device_ids=df_voltage.columns.astype(int).tolist()
    ).models()
    device_id_to_name = {device.device_id: device.name_long for device in devices}
    mask = (df_voltage > 10) & (df_apparent > 0.01)
    cec_pv_inverter_ids = list(
        set(
            [
                device.cec_pv_inverter_id
                for device in devices
                if device.cec_pv_inverter_id is not None
            ]
        )
    )
    await get_cec_pv_inverters(db, cec_pv_inverter_ids=cec_pv_inverter_ids)

    out = []
    for col in df_voltage.columns.astype(int):
        out.append(
            {
                "device_id": col,
                "device_name": device_id_to_name[col],
                "x": df_apparent.loc[mask[col]].loc[:, col].values.tolist(),
                "y": df_voltage.loc[mask[col]].loc[:, col].values.tolist(),
            }
        )
    return out
