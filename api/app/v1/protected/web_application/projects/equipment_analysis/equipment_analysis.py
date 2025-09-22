import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse
from sqlalchemy.orm import Session

from app import dependencies, utils
from app.core.current_day_pages.bess import get_bess_data
from app.core.current_day_pages.bess_pcs import get_bess_pcs_data
from app.core.current_day_pages.combiner import get_equipment_analysis_combiner_data
from app.core.current_day_pages.pcs import get_equipment_analysis_pcs_data
from app.core.current_day_pages.tracker import (
    get_tracker_by_pv_block_id_data,
    get_tracker_data,
)
from core import models

router = APIRouter(
    prefix="/equipment-analysis",
    tags=["equipment-analysis"],
    include_in_schema=utils.get_include_in_schema(),
)


@router.get(
    "/bess",
    response_class=ORJSONResponse,
)
def get_bess(
    project_id,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    project: models.Project = Depends(dependencies.get_project),
    project_db: Session = Depends(dependencies.get_project_db),
):
    return get_bess_data(
        project=project,
        project_db=project_db,
        start=start,
        end=end,
    )


@router.get(
    "/bess-pcs",
    response_class=ORJSONResponse,
)
def get_bess_pcs(
    project_id,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    project: models.Project = Depends(dependencies.get_project),
    project_db: Session = Depends(dependencies.get_project_db),
):
    return get_bess_pcs_data(
        project=project,
        project_db=project_db,
        start=start,
        end=end,
    )


@router.get(
    "/combiner",
    response_class=ORJSONResponse,
    deprecated=True,
)
def get_equipment_analysis_combiner(
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project)],
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
):
    return get_equipment_analysis_combiner_data(
        project_db=project_db,
        project=project,
        start=start,
        end=end,
    )


@router.get(
    "/tracker",
    response_class=ORJSONResponse,
)
def get_tracker(
    start: datetime.date,
    end: datetime.date,
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
    project: Annotated[models.Project, Depends(dependencies.get_project)],
    project_id,
):
    return get_tracker_data(
        start=start,
        end=end,
        project_db=project_db,
        project=project,
    )


@router.get(
    "/tracker/{pv_block_id}",
    response_class=ORJSONResponse,
)
def get_tracker_by_pv_block_id(
    pv_block_id: int,
    project_id,
    start: datetime.datetime | None = None,
    end: datetime.datetime | None = None,
    project: models.Project = Depends(dependencies.get_project),
    project_db: Session = Depends(dependencies.get_project_db),
):
    return get_tracker_by_pv_block_id_data(
        pv_block_id=pv_block_id,
        project=project,
        project_db=project_db,
        start=start,
        end=end,
    )


@router.get("/pcs", response_class=ORJSONResponse)
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
