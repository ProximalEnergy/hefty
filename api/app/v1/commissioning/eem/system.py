from typing import Annotated

import boto3
from app import dependencies, interfaces, settings
from app.domain.eem.google_sheet.read.c_read import import_google_sheet
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/projects/{project_id}/system",
    tags=["system"],
    dependencies=[Depends(dependencies.check_project_access_async)],
)


def build_project_system_file_key(*, project_name_short: str) -> str:
    """Build the S3 key used for imported system parquet files."""
    return f"{project_name_short}.parquet"


@router.put("/import")
async def put_project_system_import(
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    project: Annotated[interfaces.Project, Depends(dependencies.get_project_api)],
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


@router.get("/file-status")
def get_project_system_file_status(
    project: Annotated[interfaces.Project, Depends(dependencies.get_project_api)],
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
