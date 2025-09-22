import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse
from sqlalchemy.orm import Session

from app import dependencies, utils
from app.core.current_day_pages.pcs import get_equipment_analysis_pcs_data
from core import models

DESCRIPTION_404 = "Device not found"

router = APIRouter(
    prefix="/projects/{project_id}/equipment-analysis",
    tags=["project_equipment_analysis"],
    include_in_schema=utils.get_include_in_schema(),
)


@router.get("/pcs", response_class=ORJSONResponse, deprecated=True)
def get_equipment_analysis_pcs(
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    project_db: Session = Depends(dependencies.get_project_db),
    project: models.Project = Depends(dependencies.get_project),
):
    return get_equipment_analysis_pcs_data(
        start=start,
        end=end,
        project_db=project_db,
        project=project,
    )
