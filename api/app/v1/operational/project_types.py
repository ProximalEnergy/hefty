from typing import Annotated

from core.database import get_db
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import interfaces
from app._crud.operational.project_types import (
    get_project_types as crud_get_project_types,
)

router = APIRouter(prefix="/project-types", tags=["project_types"])


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
