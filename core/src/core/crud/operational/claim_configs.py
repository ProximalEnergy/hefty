from typing import Any, Literal
from uuid import UUID

import sqlalchemy as sa

from core import enumerations, models
from core.db_query import DbQuery


def query_claim_configs(
    *,
    project_id: UUID,
    submitter_company_id: UUID | None = None,
) -> DbQuery[Any, Literal[False]]:
    """Build a query for claim configs with counterparty names.

    Args:
        project_id: Operational project id to filter by.
        submitter_company_id: Optional submitting company id filter.
    """
    stmt = (
        sa.select(
            models.ClaimConfig.claim_config_id,
            models.ClaimConfig.submitter_company_id,
            models.ClaimConfig.counterparty_company_id,
            models.ClaimConfig.project_id,
            models.ClaimConfig.default_submission_channel,
            models.ClaimConfig.default_contact,
            models.ClaimConfig.portal_url,
            models.Company.name_long.label("counterparty_name"),
        )
        .join(
            models.Company,
            models.ClaimConfig.counterparty_company_id == models.Company.company_id,
        )
        .where(models.ClaimConfig.project_id == project_id)
    )
    if submitter_company_id is not None:
        stmt = stmt.where(
            models.ClaimConfig.submitter_company_id == submitter_company_id
        )
    return DbQuery(query=stmt)


def query_claim_config(
    *,
    claim_config_id: int,
) -> DbQuery[models.ClaimConfig, Literal[True]]:
    """Build a query for a single claim config.

    Args:
        claim_config_id: Config id to fetch.
    """
    stmt = sa.select(models.ClaimConfig).where(
        models.ClaimConfig.claim_config_id == claim_config_id
    )
    return DbQuery(query=stmt, is_scalar=True)


def insert_claim_config(
    *,
    submitter_company_id: UUID,
    counterparty_company_id: UUID,
    project_id: UUID | None,
    default_submission_channel: enumerations.ClaimSubmissionChannel,
    default_contact: str | None,
    portal_url: str | None,
) -> DbQuery[Any, Literal[True]]:
    """Build an insert for a claim config row.

    Args:
        submitter_company_id: Company filing claims.
        counterparty_company_id: OEM / counterparty.
        project_id: Optional project scope.
        default_submission_channel: Default channel.
        default_contact: Optional default contact.
        portal_url: Optional portal URL.
    """
    stmt = (
        sa.insert(models.ClaimConfig)
        .values(
            submitter_company_id=submitter_company_id,
            counterparty_company_id=counterparty_company_id,
            project_id=project_id,
            default_submission_channel=default_submission_channel,
            default_contact=default_contact,
            portal_url=portal_url,
        )
        .returning(models.ClaimConfig.claim_config_id)
    )
    return DbQuery(query=stmt, is_scalar=True)


def query_update_claim_config(
    *,
    claim_config_id: int,
    values: dict[str, Any],
) -> DbQuery[Any, Literal[True]]:
    """Build an update for a claim config row.

    Args:
        claim_config_id: Claim config primary key.
        values: Column values to update.
    """
    stmt = (
        sa.update(models.ClaimConfig)
        .where(models.ClaimConfig.claim_config_id == claim_config_id)
        .values(**values)
        .returning(models.ClaimConfig.claim_config_id)
    )
    return DbQuery(query=stmt, is_scalar=True)


def query_delete_claim_config(
    *,
    claim_config_id: int,
) -> DbQuery[Any, Literal[True]]:
    """Build a delete for a claim config row.

    Args:
        claim_config_id: Claim config primary key.
    """
    stmt = (
        sa.delete(models.ClaimConfig)
        .where(models.ClaimConfig.claim_config_id == claim_config_id)
        .returning(models.ClaimConfig.claim_config_id)
    )
    return DbQuery(query=stmt, is_scalar=True)
