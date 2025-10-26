from typing import Annotated

from app import dependencies
from app.domain.eem.google_sheet.read.c_read import import_google_sheet
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from core import models

router = APIRouter(prefix="/projects/{project_id}/system", tags=["system"])


@router.get("/health")
def health_check():
    system = {"response": 200}
    return system


@router.put(
    "/import",
    summary="read google sheets data into the s3 parquet",
)
async def import_google_sheet_route(
    *,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project)],
):
    return await import_google_sheet(
        db=db,
        project_db=project_db,
        project=project,
    )
