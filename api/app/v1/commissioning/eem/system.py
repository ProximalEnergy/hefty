from typing import Annotated

from app import dependencies, interfaces
from app.domain.eem.google_sheet.read.c_read import import_google_sheet
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/projects/{project_id}/system",
    tags=["system"],
    dependencies=[Depends(dependencies.check_project_access_async)],
)


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
