import uuid
from typing import Annotated, Any

from core.database import get_db_async
from core.db_query import DbQuery, OutputType
from core.models import Company, Contract, ContractKPI, DeviceType, KPIInstance, KPIType
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app import interfaces
from app.logger import logger

router = APIRouter(prefix="/kpi-types", tags=["project_kpi_types"])


@router.get(
    "",
    response_model=list[interfaces.KPITypeWithContractInfo],
    operation_id="get_kpi_types_by_project",
)
async def get_kpi_types_by_project(
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_async)],
):
    """Get all KPI types and their associated contract info for a project.

    Args:
        project_id: Project UUID from path parameter.
        db: Database session.
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

        results: list[Any] = await DbQuery(query=query).get_async(
            executor=db,
            output_type=OutputType.SQLALCHEMY,
        )

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
        return list(kpi_types_dict.values())

    except Exception as e:
        logger.exception("Error in get_kpi_types_by_project")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
