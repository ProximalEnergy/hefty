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
from app.logger import get_logger

logger = get_logger(name=__name__)

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
                KPIType.kpi_type_id,
                KPIType.device_type_id,
                KPIType.name_short,
                KPIType.name_long,
                KPIType.name_metric,
                KPIType.description,
                KPIType.unit,
                KPIType.aggregation_method,
                KPIType.doc_url,
                DeviceType.name_short.label("device_type_name_short"),
                Company.name_long.label("provider_name"),
                Company2.name_long.label("counter_name"),
                DeviceType.name_long.label("device_type_name"),
                DeviceType.description.label("device_type_description"),
                ContractKPI.contract_id.label("contract_kpi_contract_id"),
                ContractKPI.kpi_type_id.label("contract_kpi_type_id"),
                ContractKPI.threshold,
                ContractKPI.liquidated_damages,
                ContractKPI.claim_howto,
                ContractKPI.provider_responsible,
                Contract.contract_id,
                Contract.project_id.label("contract_project_id"),
                Contract.execution_date,
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

        results = await DbQuery(query=query).get_async(
            executor=db,
            output_type=OutputType.POLARS,
        )

        # Group results by KPI type
        kpi_types_dict: dict[int, dict[str, Any]] = {}
        for row in results.iter_rows(named=True):
            kpi_type_id = row["kpi_type_id"]
            if kpi_type_id not in kpi_types_dict:
                kpi_types_dict[kpi_type_id] = {
                    "kpi_type_id": kpi_type_id,
                    "device_type_id": row["device_type_id"],
                    "device_type_name": row["device_type_name"],
                    "name_short": row["name_short"],
                    "name_long": row["name_long"],
                    "name_metric": row["name_metric"],
                    "description": row["description"],
                    "unit": row["unit"],
                    "aggregation_method": row["aggregation_method"],
                    "device_type": {
                        "device_type_id": row["device_type_id"],
                        "name_short": row["device_type_name_short"],
                        "name_long": row["device_type_name"],
                        "description": row["device_type_description"],
                    }
                    if row["device_type_id"] is not None
                    else None,
                    "is_visible": (
                        row["is_visible"] if row["is_visible"] is not None else False
                    ),
                    "contract_kpis": [],
                    "contracts": [],
                    "doc_url": row["doc_url"],
                }

            if row["contract_kpi_contract_id"] is not None:
                contract_kpi_dict = {
                    "contract_id": row["contract_kpi_contract_id"],
                    "kpi_type_id": row["contract_kpi_type_id"],
                    "threshold": row["threshold"],
                    "liquidated_damages": row["liquidated_damages"],
                    "claim_howto": row["claim_howto"],
                    "provider_responsible": row["provider_responsible"],
                }
                kpi_types_dict[kpi_type_id]["contract_kpis"].append(
                    contract_kpi_dict,
                )

            if row["contract_id"] is not None:
                contract_dict = {
                    "contract_id": row["contract_id"],
                    "project_id": row["contract_project_id"],
                    "execution_date": row["execution_date"],
                    "provider_company": row["provider_name"],
                    "counter_company": row["counter_name"],
                }
                if contract_dict not in kpi_types_dict[kpi_type_id]["contracts"]:
                    kpi_types_dict[kpi_type_id]["contracts"].append(
                        contract_dict,
                    )

        # Convert to list and ensure is_visible is included
        return list(kpi_types_dict.values())

    except Exception as e:
        logger.exception("Error in get_kpi_types_by_project")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
