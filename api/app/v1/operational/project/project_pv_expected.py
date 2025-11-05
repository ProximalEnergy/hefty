import datetime
from typing import Annotated

from core.dependencies import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app._crud.projects.pv_expected import get_pv_expected as crud_get_pv_expected
from app.dependencies import get_project_api, get_project_db
from core import models

DESCRIPTION_404 = "Tag not found"

router = APIRouter(
    prefix="/projects/{project_id}/pv-expected", tags=["project_pv_expected"]
)


@router.get("/")
def get_expected_power(
    db: Annotated[Session, Depends(get_db)],
    project_db: Annotated[Session, Depends(get_project_db)],
    project: Annotated[models.Project, Depends(get_project_api)],
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
