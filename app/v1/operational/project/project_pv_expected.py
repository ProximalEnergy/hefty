import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import dependencies
from app._crud.projects.pv_expected import get_pv_expected as crud_get_pv_expected
from core import models

DESCRIPTION_404 = "Tag not found"

router = APIRouter(
    prefix="/projects/{project_id}/pv-expected", tags=["project_pv_expected"]
)


@router.get("/")
def get_expected_power(
    db: Annotated[Session, Depends(dependencies.get_db)],
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project)],
    start: datetime.datetime,
    end: datetime.datetime,
    device_ids: list[int] | None = [],
    expected_metric_ids: list[int] | None = [],
):
    data = crud_get_pv_expected(
        db=db,
        start=start,
        end=end,
        device_ids=device_ids,
        expected_metric_ids=expected_metric_ids,
    )
    return data
