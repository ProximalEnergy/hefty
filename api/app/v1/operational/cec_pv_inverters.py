from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import interfaces
from app._crud.operational.cec_pv_inverters import (
    get_cec_pv_inverters as crud_get_cec_pv_inverters,
)
from app._crud.operational.cec_pv_inverters import (
    upsert_cec_pv_inverters_bulk as crud_upsert_cec_pv_inverters_bulk,
)
from app.dependencies import get_async_db

DESCRIPTION_404 = "CEC PV Inverter not found"

router = APIRouter(prefix="/cec-pv-inverters", tags=["cec-pv-inverters"])


@router.get("", response_model=list[interfaces.CECPVInverterWithID])
async def get_cec_pv_inverters(
    cec_pv_inverter_ids: Annotated[list[int], Query()] = [],
    db: AsyncSession = Depends(get_async_db),
):
    """todo

    Args:
        cec_pv_inverter_ids: TODO: describe.
        db: TODO: describe.
    """
    return await crud_get_cec_pv_inverters(db, cec_pv_inverter_ids=cec_pv_inverter_ids)


@router.post("", response_model=list[interfaces.CECPVInverter])
async def upsert_cec_pv_inverters_bulk(
    inverters: interfaces.CECPVInverterBulkCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
):
    """todo

    Args:
        inverters: TODO: describe.
        db: TODO: describe.
    """
    return await crud_upsert_cec_pv_inverters_bulk(db, inverters=inverters.inverters)
