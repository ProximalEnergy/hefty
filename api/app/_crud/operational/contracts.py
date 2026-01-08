from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import interfaces
from core import models


async def create_contract(*, db: AsyncSession, contract: interfaces.ContractCreate):
    # Only include columns that exist on models.Contract
    """todo

    Args:
        db: TODO: describe.
        contract: TODO: describe.
    """
    payload = contract.model_dump(exclude_none=True)
    # Remove helper field if present
    payload.pop("contract_category_name_short", None)

    allowed_keys = {
        "project_id",
        "document_id",
        "company_id_provider",
        "company_id_counter",
        "execution_date",
        "contract_category_id",
        "term_start_date",
        "term_end_date",
        "counter_contact_addressee",
        "counter_contact_email",
        "counter_contact_address",
        "contract_summary",
    }
    filtered_payload = {k: v for k, v in payload.items() if k in allowed_keys}

    db_contract = models.Contract(**filtered_payload)
    db.add(db_contract)
    await db.commit()
    await db.refresh(db_contract)
    return db_contract


async def get_contracts(  # nosemgrep: python-enforce-keyword-only-args
    db: AsyncSession,
):
    """todo

    Args:
        db: TODO: describe.
    """
    result = await db.execute(select(models.Contract))
    return result.scalars().all()


async def get_project_contracts(
    db: AsyncSession,
    *,
    project_id: UUID,
):
    """todo

    Args:
        db: TODO: describe.
        project_id: TODO: describe.
    """
    query = (
        select(
            models.Contract.contract_id,
            models.Contract.project_id,
            models.Contract.document_id,
            models.Contract.company_id_provider,
            models.Contract.company_id_counter,
            models.Contract.execution_date,
            models.Contract.contract_category_id,
            models.Contract.term_start_date,
            models.Contract.term_end_date,
            models.Contract.counter_contact_addressee,
            models.Contract.counter_contact_email,
            models.Contract.counter_contact_address,
            models.Contract.contract_summary,
            models.Company.name_short,
            models.Company.name_long,
            models.Document.s3_key,
            models.Document.openai_file_id,
            models.ContractCategory.name_short.label("category_name_short"),
            models.ContractCategory.name_long.label("category_name_long"),
        )
        .join(
            models.Company,
            models.Contract.company_id_counter == models.Company.company_id,
        )
        .join(
            models.Document,
            models.Contract.document_id == models.Document.document_id,
        )
        .outerjoin(
            models.ContractCategory,
            models.Contract.contract_category_id
            == models.ContractCategory.contract_category_id,
        )
        .where(models.Contract.project_id == project_id)
    )

    result = await db.execute(query)
    return result.all()


async def get_contracts_by_document_id(
    db: AsyncSession,
    *,
    document_id: UUID,
):
    """todo

    Args:
        db: TODO: describe.
        document_id: TODO: describe.
    """
    result = await db.execute(
        select(models.Contract).where(models.Contract.document_id == document_id)
    )
    return result.scalars().all()


async def get_kpi_type_by_name_with_contracts(
    db: AsyncSession,
    *,
    name_short: str,
) -> dict | None:
    # Get the KPI type with device_type relationship loaded
    """todo

    Args:
        db: TODO: describe.
        name_short: TODO: describe.
    """
    kpi_type_result = await db.execute(
        select(models.KPIType)
        .options(selectinload(models.KPIType.device_type))
        .where(models.KPIType.name_short == name_short)
    )
    kpi_type = kpi_type_result.scalar_one_or_none()

    if not kpi_type:
        return None

    # Get associated contract KPIs and contracts with company information
    contract_kpi_result = await db.execute(
        select(models.ContractKPI).where(
            models.ContractKPI.kpi_type_id == kpi_type.kpi_type_id
        )
    )
    contract_kpis = contract_kpi_result.scalars().all()

    # Get all associated contracts with company information
    contract_ids = [ck.contract_id for ck in contract_kpis]
    result = await db.execute(
        select(
            models.Contract,
            models.Company.name_short.label("company_name_short"),
            models.Company.name_long.label("company_name_long"),
            models.Document.s3_key,
        )
        .join(
            models.Company,
            models.Contract.company_id_counter == models.Company.company_id,
        )
        .outerjoin(
            models.Document,
            models.Contract.document_id == models.Document.document_id,
        )
        .where(models.Contract.contract_id.in_(contract_ids))
    )
    contracts = result.all()

    # Convert to ContractWithCompany format
    contracts_with_company = [
        {
            "contract_id": contract.Contract.contract_id,
            "project_id": contract.Contract.project_id,
            "document_id": contract.Contract.document_id,
            "company_id_provider": contract.Contract.company_id_provider,
            "company_id_counter": contract.Contract.company_id_counter,
            "execution_date": contract.Contract.execution_date,
            "name_short": contract.company_name_short,
            "name_long": contract.company_name_long,
            "s3_key": contract.s3_key,
        }
        for contract in contracts
    ]

    return {
        "kpi_type": kpi_type,
        "contracts": contracts_with_company,
        "contract_kpis": contract_kpis,
    }


async def delete_contract(
    *, db: AsyncSession, contract_id: int, project_id: UUID
) -> bool:
    """
    Delete a contract if it has no associated Contractual KPIs.

    Args:
        db: Database session
        contract_id: ID of the contract to delete
        project_id: Project ID for validation

    Returns:
        bool: True if contract was deleted, False if not found or has KPIs

    Raises:
        ValueError: If contract has associated Contractual KPIs
    """
    # First, check if the contract exists and belongs to the project
    contract_result = await db.execute(
        select(models.Contract).where(
            models.Contract.contract_id == contract_id,
            models.Contract.project_id == project_id,
        )
    )
    contract = contract_result.scalar_one_or_none()

    if not contract:
        return False

    # Check if contract has any associated Contractual KPIs
    kpi_result = await db.execute(
        select(models.ContractKPI).where(models.ContractKPI.contract_id == contract_id)
    )
    contract_kpis = kpi_result.scalars().all()

    if contract_kpis:
        raise ValueError(
            f"Cannot delete contract {contract_id} because it has {len(contract_kpis)} "
            "associated Contractual KPIs. Please remove the KPIs first."
        )

    # Delete the contract
    delete_stmt = delete(models.Contract).where(
        models.Contract.contract_id == contract_id,
        models.Contract.project_id == project_id,
    )
    result = await db.execute(delete_stmt)
    await db.commit()

    # Check to see if contract was deleted
    contract_deleted = bool(cast(Any, result).rowcount > 0)

    return contract_deleted
