import uuid
from typing import Annotated

from core.database import get_db
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import interfaces
from app._crud.operational.kpi_instances import (
    api_get_kpi_instances as crud_get_kpi_instances,
)
from app.dependencies import get_is_superadmin_async

router = APIRouter(prefix="/kpi-instances", tags=["kpi_instances"])


@router.get(
    "",
    response_model=list[interfaces.KPIInstanceInterface],
    operation_id="get_kpi_instances",
)
def get_kpi_instances_route(
    db: Annotated[Session, Depends(get_db)],
    is_superadmin: Annotated[bool, Depends(get_is_superadmin_async)],
    project_ids: Annotated[list[uuid.UUID] | None, Query()] = [],
    kpi_type_ids: Annotated[list[int] | None, Query()] = [],
    deep: bool = False,
):
    """todo

    Args:
        db: Description for db.
        is_superadmin: Description for is_superadmin.
        project_ids: Description for project_ids.
        kpi_type_ids: Description for kpi_type_ids.
        deep: Description for deep.
    """
    if is_superadmin:
        is_visible = None
    else:
        is_visible = True

    kpi_instances = get_kpi_instances_helper(
        db,
        is_visible=is_visible,
        project_ids=project_ids,
        kpi_type_ids=kpi_type_ids,
        deep=deep,
    )

    return kpi_instances


def get_kpi_instances_helper(
    db: Session,
    *,
    is_visible: bool | None,
    kpi_type_ids: list[int] | None = None,
    project_ids: list[uuid.UUID] | None = None,
    deep: bool = False,
):
    """todo

    Args:
        db: Description for db.
        is_visible: Description for is_visible.
        kpi_type_ids: Description for kpi_type_ids.
        project_ids: Description for project_ids.
        deep: Description for deep.
    """
    project_ids = project_ids if project_ids and len(project_ids) > 0 else None
    kpi_type_ids = kpi_type_ids if kpi_type_ids and len(kpi_type_ids) > 0 else None
    kpi_instances = crud_get_kpi_instances(
        db=db,
        project_ids=project_ids,
        is_visible=is_visible,
        kpi_type_ids=kpi_type_ids,
        deep=deep,
    )

    return kpi_instances
