from typing import Literal
from uuid import UUID

from sqlalchemy import select

from core import models
from core.db_query import DbQuery


def get_contract_kpis(
    *,
    project_ids: list[UUID] | None = None,
    contract_ids: list[int] | None = None,
    kpi_type_ids: list[int] | None = None,
    provider_responsible: bool | None = None,
) -> DbQuery[models.ContractKPI, Literal[False]]:
    """Get contract KPIs for a given project and date range.

    Args:
        project_ids: List of project IDs to query.
        contract_ids: List of contract IDs to query.
        kpi_type_ids: List of KPI type IDs to query.
        provider_responsible: Whether to include only provider responsible KPIs.
    """
    stmt = select(models.ContractKPI)
    if project_ids is not None:
        stmt = stmt.join(
            models.Contract,
            models.ContractKPI.contract_id == models.Contract.contract_id,
        ).where(models.Contract.project_id.in_(project_ids))
    if contract_ids is not None:
        stmt = stmt.where(models.ContractKPI.contract_id.in_(contract_ids))
    if kpi_type_ids is not None:
        stmt = stmt.where(models.ContractKPI.kpi_type_id.in_(kpi_type_ids))
    if provider_responsible is not None:
        stmt = stmt.where(
            models.ContractKPI.provider_responsible == provider_responsible
        )

    return DbQuery(query=stmt)
