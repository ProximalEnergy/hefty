import datetime
import mimetypes
import uuid
from io import BytesIO
from typing import Annotated, Any, Literal

import boto3
import numpy as np
import pandas as pd
from core.crud.operational.kpi_data import (
    core_get_kpi_data,
    get_project_kpi_data_agg,
    get_project_kpi_data_agg_freq,
)
from core.database import get_db
from core.db_query import OutputType
from core.domain.kpis.rte import (
    get_and_calculate_rte,
)
from core.domain.kpis.rte import (
    get_project_rte as core_get_project_rte,
)
from core.enumerations import KPITypeEnum
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from pandas.tseries.offsets import DateOffset
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, aliased

from app import interfaces, utils
from app._crud.operational.kpi_types import get_kpi_types as crud_get_kpi_types
from app._crud.projects.kpi_data import (
    get_project_kpi_summary as crud_get_project_kpi_summary,
)
from app._dependencies.authentication import get_user
from app._dependencies.filtering import (
    filter_start_date_or_none_to_projects_data_access_start_date,
)
from app.dependencies import (
    get_async_db,
    get_is_superadmin_async,
    get_project_api,
    get_project_db,
)
from app.interfaces import UserAuthed
from app.v1.operational.kpi_data import get_kpi_data_helper
from app.v1.operational.kpi_instances import get_kpi_instances_helper
from app.v1.operational.project.project_documents import generate_presigned_url
from core import crud, models

router = APIRouter(
    prefix="/kpi-data",
    tags=["project_kpi_data"],
)


async def get_aggregation_method_for_kpi_type(
    *, db: AsyncSession, kpi_type_id: KPITypeEnum
) -> Literal["avg", "sum"]:
    """
    Retrieve the aggregation method for a given KPI type from the database.

    Args:
        db: Async database session.
        kpi_type_id: The KPI type ID to look up.

    Returns:
        The aggregation method as "avg" or "sum".
    """
    query = select(models.KPIType.aggregation_method).where(
        models.KPIType.kpi_type_id == kpi_type_id
    )
    result = await db.execute(query)
    aggregation_method = result.scalar_one()

    conversion: dict[str, Literal["avg", "sum"]] = {
        "average": "avg",
        "sum": "sum",
    }
    return conversion[aggregation_method]


class ProjectKPIData(BaseModel):
    """Response model for project KPI data with dates and values."""

    date: list[datetime.date]
    project_data: list[float]


@router.get(
    "/agg-freq",
    response_model=ProjectKPIData,
)
async def get_project_aggregated_kpi_data_freq(
    *,
    project_id: uuid.UUID,
    kpi_type_id: KPITypeEnum,
    start: datetime.date | None = None,
    end: datetime.date | None = None,
    frequency: Literal["month", "year"] | None = None,
    aggregation: Literal["avg", "sum"] | None = None,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    user_data: UserAuthed = Depends(get_user),
):
    """
    Get aggregated KPI data for a project with optional frequency binning.

    Args:
        project_id: Project UUID from path parameter.
        start: Start date for the data range. If None, there is no limit on
            the start date.
        end: End date for the data range. If None, there is no limit on the end date.
        kpi_type_id: The KPI type to query.
        frequency: Optional frequency for aggregation ("month" or "year").
        aggregation: Optional aggregation method ("avg" or "sum").
        db: Database session.
        user_data: Authenticated user data.

    Returns:
        ProjectKPIData with dates and aggregated values.
    """
    if project_id not in user_data.operational_project_ids:
        raise HTTPException(
            status_code=403, detail="You are not authorized to access this project"
        )

    if aggregation is None:
        aggregation = await get_aggregation_method_for_kpi_type(
            db=db, kpi_type_id=kpi_type_id
        )

    query = get_project_kpi_data_agg_freq(
        project_id=project_id,
        kpi_type_id=kpi_type_id,
        start=start,
        end=end,
        frequency=frequency,
        aggregation_method=aggregation,
    )
    result = await db.execute(query)
    rows = result.mappings().all()
    dates = [row["date"] for row in rows]
    project_data = [row["project_data"] for row in rows]
    return ProjectKPIData(date=dates, project_data=project_data)


@router.get(
    "/agg",
    response_model=float,
)
async def get_project_aggregated_kpi_data(
    *,
    project_id: uuid.UUID,
    kpi_type_id: KPITypeEnum,
    start: datetime.date | None = None,
    end: datetime.date | None = None,
    aggregation: Literal["avg", "sum"] | None = None,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    user_data: UserAuthed = Depends(get_user),
):
    """
    Get single aggregated KPI value for a project across entire date range.

    Args:
        project_id: Project UUID from path parameter.
        start: Start date for the data range.
        end: End date for the data range.
        kpi_type_id: The KPI type to query.
        aggregation: Optional aggregation method ("avg" or "sum").
        db: Database session.
        user_data: Authenticated user data.

    Returns:
        Single aggregated float value.
    """
    if project_id not in user_data.operational_project_ids:
        raise HTTPException(
            status_code=403, detail="You are not authorized to access this project"
        )

    if aggregation is None:
        aggregation = await get_aggregation_method_for_kpi_type(
            db=db, kpi_type_id=kpi_type_id
        )

    query = get_project_kpi_data_agg(
        project_id=project_id,
        kpi_type_id=kpi_type_id,
        start=start,
        end=end,
        aggregation_method=aggregation,
    )
    result = await query.get_async(output_type=OutputType.SQLALCHEMY)
    if result is None:
        raise HTTPException(status_code=404, detail="No KPI data found")
    return result


# Update the function to fetch contractual KPI type IDs along with contract IDs
def get_contractual_kpi_type_ids(*, db: Session, project_id: uuid.UUID):
    """todo

    Args:
        db: Description for db.
        project_id: Description for project_id.
    """
    contractual_kpis = db.execute(
        select(models.ContractKPI.kpi_type_id, models.ContractKPI.contract_id)
        .join(
            models.Contract,
            models.Contract.contract_id == models.ContractKPI.contract_id,
        )
        .where(models.Contract.project_id == project_id)
    ).all()
    return {kpi_type_id: contract_id for kpi_type_id, contract_id in contractual_kpis}


@router.get(
    "/kpi-summary-cards",
    response_model=list[interfaces.KPISummary],
    operation_id="get_project_kpi_summary",
)
def get_project_kpi_summary_route(
    project_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    project: Annotated[models.Project, Depends(get_project_api)],
    is_superadmin: Annotated[bool, Depends(get_is_superadmin_async)],
    kpi_type_ids: Annotated[list[int] | None, Query()] = None,
    device_type_id: int | None = None,
    contract_id: int | None = None,
    start: Annotated[
        datetime.date | None,
        Depends(filter_start_date_or_none_to_projects_data_access_start_date),
    ] = None,
):
    # Fetch contractual KPI type IDs and their contract IDs
    """todo

    Args:
        project_id: Description for project_id.
        db: Description for db.
        project: Description for project.
        is_superadmin: Description for is_superadmin.
        kpi_type_ids: Description for kpi_type_ids.
        device_type_id: Description for device_type_id.
        contract_id: Description for contract_id.
        start: Description for start.
    """
    contractual_kpi_type_ids = get_contractual_kpi_type_ids(
        db=db, project_id=project_id
    )

    if is_superadmin:
        is_visible = None
    else:
        is_visible = True

    kpi_instances = get_kpi_instances_helper(
        db,
        kpi_type_ids=kpi_type_ids,
        project_ids=[project_id],
        deep=True,
        is_visible=is_visible,
    )

    kpi_type_ids = [x.kpi_type_id for x in kpi_instances]

    if contract_id is not None:
        kpi_instances = [
            x
            for x in kpi_instances
            if contractual_kpi_type_ids.get(x.kpi_type_id) == contract_id
        ]
        kpi_type_ids = [x.kpi_type_id for x in kpi_instances]

    if not kpi_type_ids:
        return []

    if start:
        start = pd.Timestamp(start)
        end = start + DateOffset(days=1)
    else:
        # Default date range is the last 2 days
        end = pd.Timestamp.now(project.time_zone).floor("D")
        start = end - DateOffset(days=2)

    # Calculate YTD date range
    ytd_start = pd.Timestamp(year=end.year, month=1, day=1, tz=project.time_zone)
    ytd_end = end

    kpi_types = crud_get_kpi_types(db=db, kpi_type_ids=kpi_type_ids)
    if device_type_id:
        kpi_types = [x for x in kpi_types if x.device_type_id == device_type_id]
        kpi_type_ids = [x.kpi_type_id for x in kpi_types]
        kpi_instances = [x for x in kpi_instances if x.kpi_type_id in kpi_type_ids]

    start = start or pd.Timestamp.now(project.time_zone).floor("D") - DateOffset(days=1)
    data = crud_get_project_kpi_summary(
        db=db,
        project_id=project_id,
        kpi_type_ids=kpi_type_ids,
        start=start,
        end=end,
    )

    # Get YTD data
    ytd_data = crud_get_project_kpi_summary(
        db=db,
        project_id=project_id,
        kpi_type_ids=kpi_type_ids,
        start=ytd_start,
        end=ytd_end,
    )

    dict_out = {}

    # Loop over all kpi_type_instances in case data is missing
    for kpi_instance in kpi_instances:
        contract_id = contractual_kpi_type_ids.get(kpi_instance.kpi_type_id, None)
        kpi_type = [x for x in kpi_types if x.kpi_type_id == kpi_instance.kpi_type_id][
            0
        ]

        # Initialize with all fields, using None for missing data
        dict_out[kpi_instance.kpi_type_id] = {
            "title": kpi_instance.kpi_type.name_long,
            "link": kpi_instance.kpi_type.name_short.replace("_", "-"),
            "kpi_type_id": kpi_instance.kpi_type_id,
            "is_visible": kpi_instance.is_visible,
            "contract_id": contract_id,
            "value": None,
            "ytd_value": None,  # Initialize YTD value
            "info": kpi_type.description,
            "unit": kpi_type.unit,  # Always include the unit from KPI type
            "prefix": None,
            "change": None,
            "aggregation_method": kpi_type.aggregation_method,
        }

    start_of_yesterday = end - DateOffset(days=1)
    start_of_previous_day = start_of_yesterday - DateOffset(days=1)

    # Convert datetime to date for comparisons
    start_of_yesterday = start_of_yesterday.date()  # type: ignore
    start_of_previous_day = start_of_previous_day.date()  # type: ignore

    # Calculate YTD values
    for d in ytd_data:
        kpi_type = [x for x in kpi_types if x.kpi_type_id == d.kpi_type_id][0]
        if d.project_data is not None:
            if kpi_type.aggregation_method == "sum":
                # For sum, add up all values YTD
                ytd_values = [
                    x.project_data
                    for x in ytd_data
                    if x.kpi_type_id == d.kpi_type_id and x.project_data is not None
                ]
                ytd_value = sum(ytd_values)
            else:  # "average" or any other method
                # For average, take mean of all values YTD
                ytd_values = [
                    x.project_data
                    for x in ytd_data
                    if x.kpi_type_id == d.kpi_type_id and x.project_data is not None
                ]
                ytd_value = sum(ytd_values) / len(ytd_values) if ytd_values else None

            if kpi_type.unit == "%" and ytd_value is not None:
                ytd_value *= 100
            if ytd_value is not None:
                ytd_value = round(ytd_value, 1)
            dict_out[d.kpi_type_id]["ytd_value"] = ytd_value

    # Process daily values
    for d in data:
        if d.date < start_of_yesterday:
            continue

        kpi_type = [x for x in kpi_types if x.kpi_type_id == d.kpi_type_id][0]

        summary_value = d.project_data

        # Get previous day's data if available
        d_prev: list[Any] = [
            x
            for x in data
            if x.kpi_type_id == d.kpi_type_id and x.date == start_of_previous_day
        ]
        d_prev_option = d_prev[0] if len(d_prev) > 0 else None

        if d_prev_option:
            summary_value_prev = d_prev_option.project_data
        else:
            summary_value_prev = None

        # Calculate change
        if summary_value is not None and summary_value_prev is not None:
            change = summary_value - summary_value_prev
        else:
            change = None

        if kpi_type.unit == "%" and summary_value is not None:
            summary_value *= 100
            if change is not None:
                change *= 100

        if summary_value is not None:
            summary_value = round(summary_value, 1)
        if change is not None:
            change = round(change, 1)

        # Preserve contract_id and ytd_value from existing entry when updating
        existing_entry = dict_out[kpi_type.kpi_type_id]
        existing_contract_id = existing_entry.get("contract_id")
        existing_ytd_value = existing_entry.get("ytd_value")

        temp_dict = {
            "kpi_type_id": kpi_type.kpi_type_id,
            "title": kpi_type.name_long,
            "value": summary_value,
            "ytd_value": existing_ytd_value,  # Preserve YTD value
            "info": kpi_type.description,
            "unit": kpi_type.unit,  # Always include the unit from KPI type
            "prefix": f"{d.date.strftime('%Y-%m-%d')}" if summary_value else None,
            "change": change,
            "link": kpi_type.name_short.replace("_", "-"),
            "is_visible": [x for x in kpi_instances if x.kpi_type_id == d.kpi_type_id][
                0
            ].is_visible,
            "contract_id": existing_contract_id,
            "aggregation_method": kpi_type.aggregation_method,
        }
        dict_out[kpi_type.kpi_type_id] = temp_dict

    return list(dict_out.values())


@router.get(
    "/contract-kpis",
    response_model=list[interfaces.ContractKPIs],
    operation_id="get_project_contract_kpis",
)
def get_project_contract_kpis_route(
    project_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
):
    """Get all contract KPIs for a project with counterparty information

    Args:
        project_id: Description for project_id.
        db: Description for db.
    """
    # Query contract KPIs with company information

    # Create aliases for the companies
    ProviderCompany = aliased(models.Company)
    CounterCompany = aliased(models.Company)

    # Query to get contract KPIs with company names and document information
    query = (
        select(
            models.ContractKPI,
            ProviderCompany.name_long.label("provider_company"),
            CounterCompany.name_long.label("counter_company"),
            models.Document.s3_key.label("document_s3_key"),
        )
        .select_from(models.ContractKPI)
        .join(
            models.Contract,
            models.ContractKPI.contract_id == models.Contract.contract_id,
        )
        .join(
            ProviderCompany,
            models.Contract.company_id_provider == ProviderCompany.company_id,
        )
        .join(
            CounterCompany,
            models.Contract.company_id_counter == CounterCompany.company_id,
        )
        .outerjoin(
            models.Document,
            models.Contract.document_id == models.Document.document_id,
        )
        .where(models.Contract.project_id == project_id)
    )

    results = db.execute(query).all()

    # Convert to the expected format
    contract_kpis_with_counterparty = []
    for contract_kpi, provider_company, counter_company, document_s3_key in results:
        # Generate presigned document URL if s3_key exists
        document_url = None
        if document_s3_key:
            document_url = generate_presigned_url(file_key=document_s3_key)

        contract_kpis_with_counterparty.append(
            interfaces.ContractKPIs(
                contract_id=contract_kpi.contract_id,
                kpi_type_id=contract_kpi.kpi_type_id,
                threshold=contract_kpi.threshold,
                liquidated_damages=contract_kpi.liquidated_damages,
                claim_howto=contract_kpi.claim_howto,
                provider_responsible=contract_kpi.provider_responsible,
                provider_company=provider_company,
                counter_company=counter_company,
                document_url=document_url,
            )
        )

    return contract_kpis_with_counterparty


@router.get("/llm-kpis")
async def get_llm_kpis(
    project_id: uuid.UUID,
    project: Annotated[interfaces.ProjectInterface, Depends(get_project_api)],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    kpi_type_id: int | None = None,
):
    """This endpoint is for the chat application to fetch KPI data.

    Args:
        project_id: Description for project_id.
        project: Project dependency used to determine the default timezone.
        start: Description for start.
        end: Description for end.
        kpi_type_id: Description for kpi_type_id.
    """
    kpi_type_ids = [kpi_type_id] if kpi_type_id is not None else []
    if start is None or end is None:
        end_date = pd.Timestamp.now(tz=project.time_zone).floor("D").date()
        start_date = end_date - datetime.timedelta(days=1)
    else:
        start_date = start.date()
        end_date = end.date()

    df = await core_get_kpi_data(
        start=start_date,
        end=end_date,
        project_ids=[project_id],
        kpi_type_ids=kpi_type_ids,
        include_device_data=True,
    ).get_async(
        output_type=OutputType.PANDAS,
    )

    if df.empty:
        raise HTTPException(status_code=404, detail="No KPI data found")

    df = df.rename(columns={"date": "time", "device_data_json": "json"})

    df = df.sort_values(by="time")

    if "json" in df.columns and not df["json"].isnull().all():
        if df["json"].apply(lambda x: isinstance(x, dict)).any():
            json_df = pd.json_normalize(df["json"].dropna().tolist())
            df = df.join(json_df).drop("json", axis=1)

    return df.to_dict("tight")


class RTEResponse(BaseModel):
    """todo"""

    rte: float | None


@router.get("/rte")
async def get_rte(
    *,
    project_id: uuid.UUID,
    start: datetime.date,
    end: datetime.date,
    level: str = "string",
) -> RTEResponse:
    """
    Get the RTE for a project using the core/domain logic.
    Designed to be backward-compatible with the legacy endpoint.

    Args:
        project_id: The ID of the project.
        start: The start date of the period.
        end: The end date of the period (exclusive).
        level: The level of the RTE.

    Returns:
        RTEResponse: The RTE for the project.
    """
    if level != "string":
        raise HTTPException(status_code=400, detail="Invalid level")

    rte = await core_get_project_rte(
        project_ids=[project_id],
        start=start,
        end=end,
    )
    return RTEResponse(rte=rte[project_id])


@router.get("/rte-v2")
async def get_rte_v2(
    start: datetime.date,
    end: datetime.date,
    project: Annotated[models.Project, Depends(get_project_api)],
    rte_type: Literal["POI", "POI_NO_AUX", "FEEDER", "DC"] = "POI",
) -> RTEResponse:
    """
    Get the RTE for a project using the core/domain logic.
    Designed to be backward-compatible with the legacy endpoint.

    Args:
        start: The start date of the period.
        end: The end date of the period (exclusive).
        project: The project.
        rte_type: The type of RTE.

    Returns:
        RTEResponse: The RTE for the project.
    """
    rte = await get_and_calculate_rte(
        project=project,
        rte_type=rte_type,
        start=start,
        end=end,
    )
    return RTEResponse(rte=rte)


@router.get("/excel")
async def get_kpi_excel(
    project_id: uuid.UUID,
    kpi_type_id: int,
    start: datetime.date,
    end: datetime.date,
    sync_db: Annotated[Session, Depends(get_db)],
    project_db: Annotated[Session, Depends(get_project_db)],
    project: Annotated[models.Project, Depends(get_project_api)],
):
    """Download KPI data as an Excel file, saved to S3 and returned as a presigned URL.

    Args:
        project_id: The project UUID.
        kpi_type_id: The KPI type ID.
        start: Start date.
        end: End date.
        sync_db: Synchronous database session.
        project_db: Project-specific database session.
        project: The project model.
    """
    kpi_data = await get_kpi_data_helper(
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
        device_ids = [int(device_id) for device_id in device_df.columns.to_list()]
        devices_df = await crud.project.devices.get_project_devices(
            device_ids=device_ids,
        ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
        devices_df = devices_df.copy()
        devices_df["name_long"] = devices_df["name_long"].fillna("")
        device_types_df = await crud.operational.device_types.get_device_types(
            device_type_ids=np.unique(
                devices_df["device_type_id"].astype(int),
            ).tolist(),
        ).get_async(output_type=OutputType.POLARS)
        device_types_dict = (
            dict(
                zip(
                    device_types_df["device_type_id"].to_list(),
                    device_types_df["name_long"].to_list(),
                    strict=True,
                )
            )
            if not device_types_df.is_empty()
            else {}
        )
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
        .T.loc[["name_long", "description", "aggregation_method", "unit"]]
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
        content_type = "application/octet-stream"
    tags = "temporary"
    content_disposition = f'attachment; filename="{filename}"'

    presigned_url = None
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_key,
            Body=file_content,
            ContentType=content_type,
            Tagging=tags,
        )
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": bucket_name,
                "Key": file_key,
                "ResponseContentDisposition": content_disposition,
            },
            ExpiresIn=3600,
        )
    except Exception:
        presigned_url = None

    return presigned_url
