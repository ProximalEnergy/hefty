import datetime
from typing import Annotated

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import core
from app.dependencies import get_project_api, get_project_db
from core import models

DESCRIPTION_404 = "Tag not found"

router = APIRouter(
    prefix="/projects/{project_id}/pv-expected", tags=["project_pv_expected"]
)


@router.get("/")
def get_expected_power(
    project_db: Annotated[Session, Depends(get_project_db)],
    project: Annotated[models.Project, Depends(get_project_api)],
    start: datetime.datetime,
    end: datetime.datetime,
    device_ids: Annotated[list[int], Query()] = [],
    expected_metric_ids: Annotated[list[int], Query()] = [],
    highest_priority_only: bool = False,
):
    project_device_id = 1  # The device_id whose device_type_id is 1 (Project). This is always device_id = 1.'
    if device_ids == []:
        return []

    requested_device_ids = list(set(device_ids))
    query_device_ids = requested_device_ids.copy()
    if project_device_id not in requested_device_ids:
        query_device_ids.append(project_device_id)

    devices = core.crud.project.devices.get_project_devices(
        db=project_db, device_ids=query_device_ids
    ).pandas_dataframe(index="device_id")
    device_types = {
        1: "Project",
        2: "PV_PCS",
        5: "Meter",
        9: "PV_DC_Combiner",
    }

    devices["requested"] = devices.index.isin(requested_device_ids)

    # Allow the user to retrieve project-level data by requesting either project or meter.
    requested_has_project = (
        devices["requested"] & (devices["device_type_id"] == 1)
    ).any()

    requested_has_meter = (
        devices["requested"] & (devices["device_type_id"] == 5)
    ).any()

    if requested_has_project | requested_has_meter:
        # User explicitly asked for project (type 1), or meter (type 5).
        # Per the substitution rule, remove meters (type 5) if present.
        devices = devices.loc[devices["device_type_id"] != 5]

    else:
        # User didn't ask for project or meter.
        # Drop the project device we added as a helper.
        devices = devices.loc[devices["device_type_id"] != 1]

    devices = devices.drop(columns=["requested"])

    start_query = pd.Timestamp(start).tz_convert(project.time_zone)
    end_query = pd.Timestamp(end).tz_convert(project.time_zone)
    eem_priority_expected_metric_ids = [[12, 11, 5, 6], [10, 9, 3, 4], [8, 7, 1, 2]]
    data = core.crud.project.data_expected.get_project_data_expected(
        project_db=project_db,
        start=start_query,
        end=end_query,
        device_ids=devices.index.tolist(),
        expected_metric_ids=expected_metric_ids,
    )
    df = (
        data.pandas_dataframe().pivot(
            index="time", columns=["device_id", "expected_metric_id"], values="value"
        )
        / 1_000_000  ## W -> MW
    )
    df = df.reindex(pd.date_range(start_query, end_query, freq="5min")).ffill()
    df = df.fillna(0)
    df = df.replace(np.nan, None)

    # If highest_priority_only is True, filter to keep only the highest priority
    # expected_metric_id for each device_id
    if highest_priority_only and isinstance(df.columns, pd.MultiIndex):
        # Extract device_id and expected_metric_id from MultiIndex columns
        device_metric_pairs = df.columns.to_frame(index=False)
        device_metric_pairs.columns = ["device_id", "expected_metric_id"]

        # For each device_id, find which priority list it belongs to and get
        # the highest priority metric (first in that list)
        columns_to_keep = []
        for device_id in device_metric_pairs["device_id"].unique():
            device_metrics = device_metric_pairs[
                device_metric_pairs["device_id"] == device_id
            ]["expected_metric_id"].values

            # Find which priority list contains this device's metrics
            # (all metrics for a device come from the same priority list)
            highest_priority_metric = None
            for priority_list in eem_priority_expected_metric_ids:
                # Check if any device metric is in this priority list
                matching_metrics = [m for m in device_metrics if m in priority_list]
                if matching_metrics:
                    # Get the first (highest priority) metric from this list
                    # that exists in the device's data
                    for metric in priority_list:
                        if metric in matching_metrics:
                            highest_priority_metric = metric
                            break
                    break

            # Keep only the highest priority metric column for this device
            if highest_priority_metric is not None:
                columns_to_keep.append((device_id, highest_priority_metric))

        # Filter dataframe to keep only the selected columns (vectorized)
        if columns_to_keep:
            df = df.loc[:, columns_to_keep]

    # Build list of all (device_id, expected_metric_id) pairs to return
    dat = []
    if isinstance(df.columns, pd.MultiIndex):
        # Iterate over all column pairs in the dataframe
        for device_id, expected_metric_id in df.columns:
            # Extract scalar values - get as Series then extract first value
            device_type_id_series = devices.loc[[device_id], "device_type_id"]
            device_type_id = int(device_type_id_series.iloc[0])
            device_type_name = device_types.get(device_type_id, "Unknown")
            device_name_long_series = devices.loc[[device_id], "name_long"]
            device_name_long = str(device_name_long_series.iloc[0])
            base_name = f"{device_type_name}_Expected_Power_{device_name_long}_PROX"
            name_with_metric = f"{base_name}_E{expected_metric_id}"

            dat.append(
                {
                    "device_id": device_id,
                    "device_name_long": device_name_long,
                    "name": name_with_metric,
                    "sensor_type_name": "pv_pcs_expected_power",
                    "tag_id": -device_id,
                    "tag_name_long": "",
                    "tag_name_scada": name_with_metric,
                    "x": df.index.tolist(),
                    "y": df[(device_id, expected_metric_id)].tolist(),
                    "y_range": df[(device_id, expected_metric_id)].tolist(),
                    "yaxis": "y",
                }
            )
    else:
        # Fallback if columns are not MultiIndex (shouldn't happen)
        for device_id in df.columns:
            # Ensure device_id is an int for type safety
            device_id_int = int(device_id)
            # Extract scalar values - get as Series then extract first value
            device_type_id_series = devices.loc[[device_id_int], "device_type_id"]
            device_type_id = int(device_type_id_series.iloc[0])
            device_type_name = device_types.get(device_type_id, "Unknown")
            device_name_long_series = devices.loc[[device_id_int], "name_long"]
            device_name_long = str(device_name_long_series.iloc[0])
            base_name = f"{device_type_name}_Expected_Power_{device_name_long}_PROX"

            dat.append(
                {
                    "device_id": device_id_int,
                    "device_name_long": device_name_long,
                    "name": base_name,
                    "sensor_type_name": "pv_pcs_expected_power",
                    "tag_id": -device_id_int,
                    "tag_name_long": "",
                    "tag_name_scada": base_name,
                    "x": df.index.tolist(),
                    "y": df[device_id].tolist(),
                    "y_range": df[device_id].tolist(),
                    "yaxis": "y",
                }
            )

    return dat
