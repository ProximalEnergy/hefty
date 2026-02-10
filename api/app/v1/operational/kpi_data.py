import datetime
import mimetypes
import uuid
from io import BytesIO
from typing import Annotated

import boto3
import numpy as np
import pandas as pd
from core.crud.operational.device_types import get_device_types
from core.database import get_db
from core.db_query import OutputType
from fastapi import APIRouter, Depends, Query, UploadFile
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import core
from app import interfaces, utils
from app._crud.operational.kpi_data import get_kpi_data as crud_get_kpi_data
from app._crud.operational.kpi_types import get_kpi_types as crud_get_kpi_types
from app.dependencies import (
    check_project_access_async,
    get_async_db,
    get_project_api,
    get_project_db,
    get_user_data_async,
)
from core import models

router = APIRouter(prefix="/kpi-data", tags=["kpi_data"])


@router.get(
    "",
    operation_id="get_kpi_data",
    response_model=list[interfaces.OperationalKPIData],
    response_class=ORJSONResponse,
)
def get_kpi_data(
    start: datetime.date,
    end: datetime.date,
    project_ids: Annotated[list[uuid.UUID], Query()] = [],
    kpi_type_ids: Annotated[list[int], Query()] = [],
    include_device_data: bool = True,
    db: Session = Depends(get_db),
    user_data: interfaces.UserData = Depends(get_user_data_async),
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
        db: Description for db.
        user_data: Description for user_data.
        include_all_dates: Description for include_all_dates.
    """
    project_ids = list(set(project_ids) & set(user_data.operational_project_ids))

    # NOTE: Logic was separated out into a helper function so that other endpoints can
    # use the same logic
    return get_kpi_data_helper(
        db=db,
        start=start,
        end=end,
        project_ids=project_ids,
        kpi_type_ids=kpi_type_ids,
        include_device_data=include_device_data,
        include_all_dates=include_all_dates,
    )


def get_kpi_data_helper(
    *,
    db: Session,
    start: datetime.date,
    end: datetime.date,
    project_ids: list[uuid.UUID],
    kpi_type_ids: list[int],
    include_device_data: bool,
    include_all_dates: bool = True,
):
    """todo

    Args:
        db: Description for db.
        start: Description for start.
        end: Description for end.
        project_ids: Description for project_ids.
        kpi_type_ids: Description for kpi_type_ids.
        include_device_data: Description for include_device_data.
        include_all_dates: Description for include_all_dates.
    """
    date_range = pd.date_range(start=start, end=end, freq="D", inclusive="left")

    # Query KPI data
    kpi_data = crud_get_kpi_data(
        db=db,
        start=start,
        end=end,
        kpi_type_ids=kpi_type_ids,
        project_ids=project_ids,
        include_device_data=include_device_data,
    )

    kpi_data = kpi_data.sort_values(by=["project_id", "kpi_type_id", "date"])

    # Identify unique project_id-kpi_type_id combinations
    uniques = kpi_data[["project_id", "kpi_type_id"]].drop_duplicates()

    return_data = []

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

        data = {
            "project_id": unique.project_id,
            "kpi_type_id": unique.kpi_type_id,
            "data": {
                "dates": unique_kpi_data.index.tolist(),
                "project_data": unique_kpi_data["project_data"].values.tolist(),
                # TODO: Refactor database schema to include separate weights column
                "weights": None,
            },
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

            data["data"]["device_data_obj"] = {"device_values": device_values}

            # Convert device_values to a DataFrame
            # with specified dtype, None's will be converted to NaN
            # device_values_df = pd.DataFrame(device_values, dtype=np.float64).T

            # Pandas handled statistics
            if device_values_df.empty:
                device_agg_df = pd.DataFrame(
                    columns=[
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
                )
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

            data["data"]["device_aggregation_obj"] = device_agg_df.to_dict(
                orient="list",
            )

        # If device data is not requested or not available, set device_data_obj to None
        else:
            data["data"]["device_data_obj"] = None
            data["data"]["device_aggregation_obj"] = None

        return_data.append(data)

    return return_data


@router.get(
    "/{project_id}/excel",
    dependencies=[Depends(check_project_access_async)],
)
async def get_kpi_excel(
    project_id: uuid.UUID,
    kpi_type_id: int,
    start: datetime.date,
    end: datetime.date,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    sync_db: Annotated[Session, Depends(get_db)],
    project_db: Annotated[Session, Depends(get_project_db)],
    project: Annotated[models.Project, Depends(get_project_api)],
):
    """todo

    Args:
        project_id: Description for project_id.
        kpi_type_id: Description for kpi_type_id.
        start: Description for start.
        end: Description for end.
        db: Description for db.
        sync_db: Description for sync_db.
        project_db: Description for project_db.
        project: Description for project.
    """
    kpi_data = get_kpi_data_helper(
        db=sync_db,
        start=start,
        end=end,
        project_ids=[project_id],
        kpi_type_ids=[kpi_type_id],
        include_device_data=True,
    )
    kpi_type = crud_get_kpi_types(db=sync_db, kpi_type_ids=[kpi_type_id])[0]

    has_device_data = kpi_data[0]["data"]["device_data_obj"] is not None

    device_df = None
    if has_device_data:
        device_df = pd.DataFrame(
            kpi_data[0]["data"]["device_data_obj"]["device_values"],
            index=kpi_data[0]["data"]["dates"],
        )
        project_schema = utils.get_project_schema(project_db=project_db)
        devices_df = await core.crud.project.devices.get_project_devices(
            device_ids=device_df.columns.astype(int).tolist(),
        ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
        devices_df = devices_df.copy()
        devices_df["name_long"] = devices_df["name_long"].fillna("")
        device_types = await get_device_types(
            db=db,
            device_type_ids=np.unique(
                devices_df["device_type_id"].astype(int),
            ).tolist(),
        )
        device_types_dict = {
            device_type.device_type_id: device_type.name_long
            for device_type in device_types
        }
        device_id_to_name_full = {
            int(device["device_id"]): (
                f"{device_types_dict[int(device['device_type_id'])]} "
                f"{device.get('name_long')}"
            )
            for device in devices_df.to_dict("records")
        }
        device_df = device_df.rename(columns=device_id_to_name_full)
        device_df.index.name = "Date"
    project_df = pd.DataFrame(
        kpi_data[0]["data"]["project_data"],
        index=kpi_data[0]["data"]["dates"],
    ).rename(columns={0: "Project"})
    project_df.index.name = "Date"
    metadata_df = (
        pd.DataFrame(kpi_type.__dict__, index=["Value"])
        .T.loc[["name_long", "description", "aggregation_method", "unit"]]  # type: ignore
        .reset_index()
        .rename(columns={"index": "Property"})
    )

    ## Excel writing, saving to S3, returning presigned URL
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
        metadata_df.to_excel(writer, sheet_name="Overview", index=False, header=True)
        if has_device_data and device_df is not None:
            if device_df.shape[1] > 16383:  ## Excel limitation
                device_df.T.to_excel(writer, sheet_name="Device Data", index=True)
            else:
                device_df.to_excel(writer, sheet_name="Device Data", index=True)
        project_df.to_excel(writer, sheet_name="Project Data", index=True)
    excel_buffer.seek(0)

    file = UploadFile(
        filename=(
            f"{project.name_short}_{kpi_type.name_short}_"
            f"{start.strftime('%Y-%m-%d')}-{end.strftime('%Y-%m-%d')}.xlsx"
        ),
        file=excel_buffer,
    )
    file_content = await file.read()
    s3_client = boto3.client("s3", region_name="us-east-2")
    prefix = "kpi-data"
    filename = file.filename
    bucket_name = "proximal-am-documents"
    file_key = f"{prefix}/{filename}"
    content_type, _ = mimetypes.guess_type(file.filename)  # type: ignore
    if content_type is None:
        content_type = "application/octet-stream"  # Default to binary if unknown
    tags = "temporary"

    # NOTE: This ensures the file is downloaded correctly in the browser.
    content_disposition = f'attachment; filename="{filename}"'

    def generate_presigned_url(*, file_key: str) -> str:
        # Generate a pre-signed URL for a file
        """todo

        Args:
            file_key: Description for file_key.
        """
        bucket_name = "proximal-am-documents"
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": bucket_name,
                "Key": file_key,
                "ResponseContentDisposition": content_disposition,
            },
            ExpiresIn=3600,  # Link expiration in seconds (1 hour)
        )
        return str(presigned_url)

    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_key,
            Body=file_content,
            ContentType=content_type,
            Tagging=tags,
        )
        presigned_url = generate_presigned_url(file_key=file_key)
    except Exception:
        presigned_url = None

    return presigned_url


@router.get(
    "/{project_id}/kpi-email-alerts",
    dependencies=[Depends(check_project_access_async)],
)
def get_kpi_email_alerts(
    start: datetime.datetime,
    end: datetime.datetime,
    kpi_type_id: int,
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """todo

    Args:
        start: Description for start.
        end: Description for end.
        kpi_type_id: Description for kpi_type_id.
        project_id: Description for project_id.
        db: Description for db.
    """
    kpi_data = get_kpi_data_helper(
        db=db,
        start=start,
        end=end,
        project_ids=[project_id],
        kpi_type_ids=[kpi_type_id],
        include_device_data=True,
    )
    return kpi_data
