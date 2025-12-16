from typing import Annotated

from core.dependencies import get_db
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import interfaces, utils
from app._crud.operational.project_types import (
    get_project_type as crud_get_project_type,
)
from app._crud.operational.project_types import (
    get_project_types as crud_get_project_types,
)

DESCRIPTION_404 = "Project type not found"

router = APIRouter(prefix="/project-types", tags=["project_types"])
deprecated_router = APIRouter(
    prefix="/project-types", tags=["project_types"], deprecated=True
)


@router.get(
    "", response_model=list[interfaces.ProjectType], operation_id="get_project_types"
)
def get_project_types(
    project_type_ids: Annotated[list[int], Query()] = [],
    name_short: str = "",
    name_long: str = "",
    db: Session = Depends(get_db),
):
    """todo

    Args:
        project_type_ids: TODO: describe.
        name_short: TODO: describe.
        name_long: TODO: describe.
        db: TODO: describe.
    """
    return crud_get_project_types(
        db=db,
        project_type_ids=project_type_ids,
        name_short=name_short,
        name_long=name_long,
    )


@deprecated_router.get(
    "",
    response_model=list[interfaces.ProjectType],
    operation_id="get_project_types_legacy",
)
def get_project_types_legacy(
    *,
    project_type_ids: Annotated[list[int], Query()] = [],
    name_short: str = "",
    name_long: str = "",
    db: Session = Depends(get_db),
):
    """todo

    Args:
        project_type_ids: TODO: describe.
        name_short: TODO: describe.
        name_long: TODO: describe.
        db: TODO: describe.
    """
    return get_project_types(
        project_type_ids=project_type_ids,
        name_short=name_short,
        name_long=name_long,
        db=db,
    )


@router.get(
    "/{project_type_id}",
    response_model=interfaces.ProjectType,
    responses={404: {"description": DESCRIPTION_404}},
    operation_id="get_project_type_by_id",
)
def get_project_type(project_type_id: int, db: Annotated[Session, Depends(get_db)]):
    """todo

    Args:
        project_type_id: TODO: describe.
        db: TODO: describe.
    """
    project_type = crud_get_project_type(db=db, project_type_id=project_type_id)
    utils.check_404(value=project_type, detail=DESCRIPTION_404)
    return project_type


@deprecated_router.get(
    "/{project_type_id}",
    response_model=interfaces.ProjectType,
    responses={404: {"description": DESCRIPTION_404}},
    operation_id="get_project_type_by_id_legacy",
)
def get_project_type_legacy(
    *, project_type_id: int, db: Annotated[Session, Depends(get_db)]
):
    """todo

    Args:
        project_type_id: TODO: describe.
        db: TODO: describe.
    """
    return get_project_type(project_type_id, db)
