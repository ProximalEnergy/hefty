import uuid
from typing import Annotated

from core.dependencies import get_db
from core.models import Company, Contract, ContractKPI, DeviceType, KPIInstance, KPIType
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, aliased

from app import interfaces
from app._crud.operational.contracts import (
    get_kpi_type_by_name_with_contracts as crud_get_kpi_type_by_name_with_contracts,
)
from app._crud.operational.kpi_types import get_kpi_types as crud_get_kpi_types
from app.dependencies import get_async_db
from app.logger import logger
from app.v1.operational.project.project_contracts import generate_presigned_url

router = APIRouter(prefix="/kpi-types", tags=["kpi_types"])


@router.get("/by-name/{name_short}", response_model=interfaces.KPITypeWithContracts)
async def get_kpi_type_by_name(
    name_short: str,
    db: Annotated[AsyncSession, Depends(get_async_db)],
):
    """todo

    Args:
        name_short: TODO: describe.
        db: TODO: describe.
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


@router.get("", response_model=list[interfaces.KPIType], operation_id="get_kpi_types")
def get_kpi_types(
    db: Annotated[Session, Depends(get_db)],
    kpi_type_ids: Annotated[list[int] | None, Query()] = None,
):
    """todo

    Args:
        db: TODO: describe.
        kpi_type_ids: TODO: describe.
    """
    return crud_get_kpi_types(db=db, kpi_type_ids=kpi_type_ids)


@router.get(
    "/{kpi_type_id}",
    response_model=interfaces.KPIType,
    operation_id="get_kpi_type_by_id",
)
def get_kpi_type(
    kpi_type_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    """todo

    Args:
        kpi_type_id: TODO: describe.
        db: TODO: describe.
    """
    return crud_get_kpi_types(db=db, kpi_type_ids=[kpi_type_id])[0]


@router.get(
    "/by-project/{project_id}",
    response_model=list[interfaces.KPITypeWithContractInfo],
    operation_id="get_kpi_types_by_project",
)
def get_kpi_types_by_project(
    project_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
):
    """todo

    Args:
        project_id: TODO: describe.
        db: TODO: describe.
    """
    try:
        # Create alias for the counter company
        Company2 = aliased(Company)

        # Query to get all KPI types and their associated contract info
        query = (
            select(
                KPIType,
                ContractKPI,
                Contract,
                Company.name_long.label("provider_name"),
                Company2.name_long.label("counter_name"),
                DeviceType.name_long.label("device_type_name"),
                KPIInstance.is_visible,
            )
            .select_from(KPIType)
            .outerjoin(DeviceType, KPIType.device_type_id == DeviceType.device_type_id)
            .outerjoin(
                KPIInstance,
                and_(
                    KPIType.kpi_type_id == KPIInstance.kpi_type_id,
                    KPIInstance.project_id == project_id,
                ),
            )
            .outerjoin(ContractKPI, KPIType.kpi_type_id == ContractKPI.kpi_type_id)
            .outerjoin(
                Contract,
                and_(
                    ContractKPI.contract_id == Contract.contract_id,
                    Contract.project_id == project_id,
                ),
            )
            .outerjoin(Company, Contract.company_id_provider == Company.company_id)
            .outerjoin(Company2, Contract.company_id_counter == Company2.company_id)
            .order_by(KPIType.kpi_type_id)
        )

        results = db.execute(query).all()

        # Group results by KPI type
        kpi_types_dict = {}
        for (
            kpi_type,
            contract_kpi,
            contract,
            provider_name,
            counter_name,
            device_type_name,
            is_visible,
        ) in results:
            if kpi_type.kpi_type_id not in kpi_types_dict:
                kpi_types_dict[kpi_type.kpi_type_id] = {
                    "kpi_type_id": kpi_type.kpi_type_id,
                    "device_type_id": kpi_type.device_type_id,
                    "device_type_name": device_type_name,
                    "name_short": kpi_type.name_short,
                    "name_long": kpi_type.name_long,
                    "name_metric": kpi_type.name_metric,
                    "description": kpi_type.description,
                    "unit": kpi_type.unit,
                    "aggregation_method": kpi_type.aggregation_method,
                    "device_type": kpi_type.device_type,
                    "is_visible": is_visible if is_visible is not None else False,
                    "contract_kpis": [],
                    "contracts": [],
                    "doc_url": kpi_type.doc_url,
                }

            if contract_kpi:
                contract_kpi_dict = {
                    "contract_id": contract_kpi.contract_id,
                    "kpi_type_id": contract_kpi.kpi_type_id,
                    "threshold": contract_kpi.threshold,
                    "liquidated_damages": contract_kpi.liquidated_damages,
                    "claim_howto": contract_kpi.claim_howto,
                    "provider_responsible": contract_kpi.provider_responsible,
                }
                kpi_types_dict[kpi_type.kpi_type_id]["contract_kpis"].append(
                    contract_kpi_dict,
                )

            if contract:
                contract_dict = {
                    "contract_id": contract.contract_id,
                    "project_id": contract.project_id,
                    "execution_date": contract.execution_date,
                    "provider_company": provider_name,
                    "counter_company": counter_name,
                }
                if (
                    contract_dict
                    not in kpi_types_dict[kpi_type.kpi_type_id]["contracts"]
                ):
                    kpi_types_dict[kpi_type.kpi_type_id]["contracts"].append(
                        contract_dict,
                    )

        # Convert to list and ensure is_visible is included
        response = list(kpi_types_dict.values())

        return response

    except Exception as e:
        logger.exception("Error in get_kpi_types_by_project")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
