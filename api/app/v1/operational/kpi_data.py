import datetime
import uuid
from typing import Annotated, Any

import numpy as np
import pandas as pd
from core.crud.operational.kpi_data import core_get_kpi_data
from core.db_query import OutputType
from fastapi import APIRouter, Depends, Query

from app import interfaces
from app._dependencies.authentication import get_user
from app._dependencies.filtering import (
    filter_start_date_to_projects_data_access_start_date,
)

router = APIRouter(prefix="/kpi-data", tags=["kpi_data"])


@router.get(
    "",
    operation_id="get_kpi_data",
    response_model=list[interfaces.OperationalKPIDataInterface],
)
async def get_kpi_data_route(
    user_data: Annotated[interfaces.UserAuthed, Depends(get_user)],
    start: Annotated[
        datetime.date, Depends(filter_start_date_to_projects_data_access_start_date)
    ],
    end: datetime.date,
    project_ids: Annotated[list[uuid.UUID], Query()] = [],
    kpi_type_ids: Annotated[list[int], Query()] = [],
    include_device_data: bool = True,
    include_all_dates: bool = True,
):
    # Ensure that user has access to all requested projects
    """todo

    Args:
        start: Description for start.
        end: Description for end.
        project_ids: Description for project_ids.
        kpi_type_ids: Description for kpi_type_ids.
        include_device_data: Description for include_device_data.
        user_data: Description for user_data.
        include_all_dates: Description for include_all_dates.
    """
    project_ids = list(set(project_ids) & set(user_data.operational_project_ids))

    # NOTE: Logic was separated out into a helper function so that other endpoints can
    # use the same logic
    return await get_kpi_data_helper(
        start=start,
        end=end,
        project_ids=project_ids,
        kpi_type_ids=kpi_type_ids,
        include_device_data=include_device_data,
        include_all_dates=include_all_dates,
    )


async def get_kpi_data_helper(
    *,
    start: datetime.date,
    end: datetime.date,
    project_ids: list[uuid.UUID],
    kpi_type_ids: list[int],
    include_device_data: bool,
    include_all_dates: bool = True,
):
    """todo

    Args:
        start: Description for start.
        end: Description for end.
        project_ids: Description for project_ids.
        kpi_type_ids: Description for kpi_type_ids.
        include_device_data: Description for include_device_data.
        include_all_dates: Description for include_all_dates.
    """
    date_range = pd.date_range(start=start, end=end, freq="D", inclusive="left")

    # Query KPI data
    kpi_data = await core_get_kpi_data(
        start=start,
        end=end,
        kpi_type_ids=kpi_type_ids,
        project_ids=project_ids,
        include_device_data=include_device_data,
    ).get_async(
        output_type=OutputType.PANDAS,
    )

    kpi_data = kpi_data.sort_values(by=["project_id", "kpi_type_id", "date"])

    # Identify unique project_id-kpi_type_id combinations
    uniques = kpi_data[["project_id", "kpi_type_id"]].drop_duplicates()

    return_data: list[dict[str, Any]] = []

    # For each unique project_id-kpi_type_id combination
    for unique in uniques.itertuples():
        # Filter DataFrame
        unique_kpi_data = kpi_data.loc[
            (kpi_data["project_id"] == unique.project_id)
            & (kpi_data["kpi_type_id"] == unique.kpi_type_id)
        ]

        unique_kpi_data = unique_kpi_data.set_index("date")
        if include_all_dates:
            unique_kpi_data = unique_kpi_data.reindex(date_range)

        data_obj: dict[str, Any] = {
            "dates": unique_kpi_data.index.tolist(),
            "project_data": unique_kpi_data["project_data"].values.tolist(),
            # TODO: Refactor database schema to include separate weights column
            "weights": None,
        }
        data: dict[str, Any] = {
            "project_id": unique.project_id,
            "kpi_type_id": unique.kpi_type_id,
            "data": data_obj,
        }

        # Only include device data if requested and device_data_json is not null
        # (a project KPI)
        if (
            include_device_data
            and not unique_kpi_data["device_data_json"].isnull().all()
        ):
            # Extract device_values from device_data_json
            # device_value_list is a list of dictionaries mapping device_id to a value
            device_values_list = (
                unique_kpi_data["device_data_json"]
                .apply(lambda x: x["device_values"] if isinstance(x, dict) else {})
                .tolist()
            )

            device_values_df = pd.DataFrame(device_values_list, dtype=np.float64)

            device_values = device_values_df.to_dict(orient="list")

            # Convert list of dictionaries to a dictionary mapping device_id to a
            # list of values
            # device_values = {
            #     int(key): [d[key] for d in device_values_list]
            #     for key in device_values_list[0]
            # }

            data_obj["device_data_obj"] = {"device_values": device_values}

            # Convert device_values to a DataFrame
            # with specified dtype, None's will be converted to NaN
            # device_values_df = pd.DataFrame(device_values, dtype=np.float64).T

            # Pandas handled statistics
            agg_columns = [
                "sum",
                "mean",
                "std",
                "min",
                "max",
                "median",
                "count",
                "range",
                "available_data",
            ]
            has_values = device_values_df.notna().any().any()
            if device_values_df.empty or not has_values:
                device_agg_df = pd.DataFrame(
                    index=device_values_df.columns,
                    columns=agg_columns,
                    dtype=np.float64,
                )
                if not device_agg_df.empty:
                    device_agg_df["count"] = 0
                    device_agg_df["available_data"] = 0
            else:
                device_agg_df = device_values_df.T.agg(
                    ["sum", "mean", "std", "min", "max", "median", "count"]
                ).T

                # Manually calculated statistics
                device_agg_df["range"] = device_agg_df["max"] - device_agg_df["min"]
                total_devices = device_values_df.shape[0]
                if total_devices > 0:
                    device_agg_df["available_data"] = (
                        device_agg_df["count"] / total_devices
                    )
                else:
                    device_agg_df["available_data"] = np.nan

            data_obj["device_aggregation_obj"] = device_agg_df.to_dict(
                orient="list",
            )

        # If device data is not requested or not available, set device_data_obj to None
        else:
            data_obj["device_data_obj"] = None
            data_obj["device_aggregation_obj"] = None

        return_data.append(data)

    return return_data
