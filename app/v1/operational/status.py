from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import core
from app.dependencies import get_db

router = APIRouter(prefix="/status", tags=["status"])


@router.get("/lookup", operation_id="get_device_statuses")
def get_statuses(
    db: Annotated[Session, Depends(get_db)],
    status_lookup_ids: Annotated[list[int], Query()] = [],
):
    status_lookup = core.crud.project.statuses.get_status_lookup(
        db,
        status_lookup_ids=status_lookup_ids,
    ).models()
    return status_lookup


@router.get("/binary", operation_id="get_device_status_binary")
def get_status_binary(
    db: Annotated[Session, Depends(get_db)],
    status_binary_ids: Annotated[list[int], Query()] = [],
):
    status_binary = core.crud.project.statuses.get_status_binary(
        db=db,
        status_binary_ids=status_binary_ids,
    ).models()
    return status_binary
