from typing import Annotated

from core.dependencies import get_db
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import interfaces, utils
from app._crud.operational.pg_data_types import (
    get_pg_data_type as crud_get_pg_data_type,
)
from app._crud.operational.pg_data_types import (
    get_pg_data_types as crud_get_pg_data_types,
)

DESCRIPTION_404 = "PG data type not found"
router = APIRouter(prefix="/pg-data-types", tags=["pg_data_types"])
deprecated_router = APIRouter(
    prefix="/pg_data_types", tags=["pg_data_types"], deprecated=True
)


@router.get("/", response_model=list[interfaces.PGDataType])
def get_pg_data_types(
    pg_data_type_ids: Annotated[list[int], Query()] = [],
    name_short: str = "",
    db: Session = Depends(get_db),
):
    return crud_get_pg_data_types(
        db=db,
        pg_data_type_ids=pg_data_type_ids,
        name_short=name_short,
    )


@deprecated_router.get("/", response_model=list[interfaces.PGDataType])
def get_pg_data_types_legacy(
    *,
    pg_data_type_ids: Annotated[list[int], Query()] = [],
    name_short: str = "",
    db: Session = Depends(get_db),
):
    return get_pg_data_types(
        pg_data_type_ids=pg_data_type_ids,
        name_short=name_short,
        db=db,
    )


@router.get(
    "/{pg_data_type_id}",
    response_model=interfaces.PGDataType,
    responses={404: {"description": DESCRIPTION_404}},
)
def get_pg_data_type(pg_data_type_id: int, db=Depends(get_db)):
    pg_data_type = crud_get_pg_data_type(db=db, pg_data_type_id=pg_data_type_id)
    utils.check_404(value=pg_data_type, detail=DESCRIPTION_404)
    return pg_data_type


@deprecated_router.get(
    "/{pg_data_type_id}",
    response_model=interfaces.PGDataType,
    responses={404: {"description": DESCRIPTION_404}},
)
def get_pg_data_type_legacy(*, pg_data_type_id: int, db=Depends(get_db)):
    return get_pg_data_type(pg_data_type_id, db)
