from collections.abc import Generator
from typing import Annotated
from uuid import UUID

import boto3
from app import dependencies, interfaces, settings
from app._dependencies.authorization import require_user_project
from app.domain.eem.google_sheet.inverter_met_mapping import (
    map_inverters_to_met_stations as met_station_mapping,
)
from app.domain.eem.google_sheet.read.c_read import import_google_sheet
from botocore.exceptions import ClientError
from core.database import with_db
from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session


class InverterMetStationMappingResponse(BaseModel):
    """Response for Google Sheet inverter to met station mapping."""

    rows_updated: int
    inverters_mapped: int
    met_stations_available: int


def build_project_system_file_key(*, project_name_short: str) -> str:
    """Build the S3 key used for imported system parquet files.

    Args:
        project_name_short: Short project name used as the filename stem.
    """
    return f"{project_name_short}.parquet"


router = APIRouter(
    prefix="/system/{project_id}",
    tags=["system"],
    dependencies=[Depends(require_user_project)],
)


def get_project_system_db(
    *, project_id: UUID = Path(...)
) -> Generator[Session, None, None]:
    """Get the project database from the system endpoint path parameter.

    Args:
        project_id: Project UUID used to resolve the tenant schema.
    """
    project_name_short = dependencies.get_project_name_short(project_id=project_id)

    with with_db(schema=project_name_short) as project_db:
        yield project_db


@router.put("/import")
async def put_project_system_import(
    project_db: Annotated[Session, Depends(get_project_system_db)],
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    project: Annotated[
        interfaces.ProjectInterface, Depends(dependencies.get_project_api)
    ],
):
    """
    Import system data from Google Sheets into S3.
    Args:
        project_db: The database session for the project.
        db: The database session for the project.
        project: The project object.
    """
    await import_google_sheet(
        db=db,
        project_db=project_db,
        project=project,
    )
    return {"message": "System data imported successfully"}


@router.put(
    "/map-inverters-to-met-stations",
    response_model=InverterMetStationMappingResponse,
)
async def put_project_system_map_inverters_to_met_stations(
    project_db: Annotated[Session, Depends(get_project_system_db)],
    project: Annotated[
        interfaces.ProjectInterface, Depends(dependencies.get_project_api)
    ],
):
    """Populate Google Sheet Met Name values from nearest met station devices.

    Args:
        project_db: The database session for the project.
        project: The project object.
    """
    google_sheet_id = project.gsheet_id
    if google_sheet_id is None:
        raise HTTPException(status_code=404, detail="Google Sheet ID not found")

    return await met_station_mapping.map_inverters_to_met_stations(
        project_db=project_db,
        spreadsheet_id=google_sheet_id,
    )


@router.get("/file-status")
def get_project_system_file_status(
    project: Annotated[
        interfaces.ProjectInterface, Depends(dependencies.get_project_api)
    ],
):
    """Return existence status for the system import output file in S3."""
    bucket_name = settings.AWS_S3_BUCKET_NAME
    if not bucket_name:
        raise HTTPException(
            status_code=500,
            detail="AWS_S3_BUCKET_NAME is not configured",
        )

    file_key = build_project_system_file_key(project_name_short=project.name_short)
    s3_client = boto3.client("s3", region_name="us-east-2")

    try:
        s3_client.head_object(Bucket=bucket_name, Key=file_key)
        exists = True
    except ClientError as error:
        error_code = str(error.response.get("Error", {}).get("Code", ""))
        if error_code in {"404", "NoSuchKey", "NotFound"}:
            exists = False
        else:
            raise HTTPException(
                status_code=500,
                detail="Unable to check system file status",
            ) from error

    return {
        "bucket_name": bucket_name,
        "file_key": file_key,
        "exists": exists,
    }
