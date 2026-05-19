from typing import Annotated

from core.database import get_db
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app import interfaces
from app._crud.operational.contracts import (
    get_kpi_type_by_name_with_contracts as crud_get_kpi_type_by_name_with_contracts,
)
from app._crud.operational.kpi_types import get_kpi_types as crud_get_kpi_types
from app.dependencies import get_async_db
from app.logger import get_logger
from app.v1.operational.project.project_contracts import generate_presigned_url

logger = get_logger(name=__name__)

router = APIRouter(prefix="/kpi-types", tags=["kpi_types"])


@router.get("/by-name/{name_short}", response_model=interfaces.KPITypeWithContracts)
async def get_kpi_type_by_name(
    name_short: str,
    db: Annotated[AsyncSession, Depends(get_async_db)],
):
    """todo

    Args:
        name_short: Description for name_short.
        db: Description for db.
    """
    try:
        # Convert hyphens to underscores for database lookup
        name_short = name_short.replace("-", "_")

        result = await crud_get_kpi_type_by_name_with_contracts(
            db, name_short=name_short
        )
        if not result:
            raise HTTPException(status_code=404, detail="KPI type not found")

        # Convert contracts to include document URLs
        contracts_with_urls = []
        for contract in result["contracts"]:
            contract_dict = contract.copy()  # Create a copy of the contract dict
            if contract_dict["s3_key"]:
                contract_dict["document_url"] = generate_presigned_url(
                    file_key=contract_dict["s3_key"],
                )
            contracts_with_urls.append(contract_dict)

        # Convert contract KPIs to dict
        contract_kpis_dict = [
            {
                "contract_id": ck.contract_id,
                "kpi_type_id": ck.kpi_type_id,
                "threshold": ck.threshold,
                "liquidated_damages": ck.liquidated_damages,
                "claim_howto": ck.claim_howto,
                "provider_responsible": ck.provider_responsible,
            }
            for ck in result["contract_kpis"]
        ]

        # Construct the response
        response = {
            "kpi_type_id": result["kpi_type"].kpi_type_id,
            "device_type_id": result["kpi_type"].device_type_id,
            "name_short": result["kpi_type"].name_short,
            "name_long": result["kpi_type"].name_long,
            "name_metric": result["kpi_type"].name_metric,
            "description": result["kpi_type"].description,
            "unit": result["kpi_type"].unit,
            "aggregation_method": result["kpi_type"].aggregation_method,
            "device_type": result["kpi_type"].device_type,
            "contracts": contracts_with_urls,
            "contract_kpis": contract_kpis_dict,
            "doc_url": result["kpi_type"].doc_url,
        }

        return response

    except Exception as e:
        logger.exception("Error in get_kpi_type_by_name")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "", response_model=list[interfaces.KPITypeInterface], operation_id="get_kpi_types"
)
def get_kpi_types_route(
    db: Annotated[Session, Depends(get_db)],
    kpi_type_ids: Annotated[list[int] | None, Query()] = None,
):
    """todo

    Args:
        db: Description for db.
        kpi_type_ids: Description for kpi_type_ids.
    """
    return crud_get_kpi_types(db=db, kpi_type_ids=kpi_type_ids)


@router.get(
    "/{kpi_type_id}",
    response_model=interfaces.KPITypeInterface,
    operation_id="get_kpi_type_by_id",
)
def get_kpi_type(
    kpi_type_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """todo

    Args:
        kpi_type_id: Description for kpi_type_id.
        db: Description for db.
    """
    return crud_get_kpi_types(db=db, kpi_type_ids=[kpi_type_id])[0]
