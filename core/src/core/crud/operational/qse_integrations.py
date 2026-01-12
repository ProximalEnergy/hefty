from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from core.db_query import DbQuery
from core.models import QSEField, QSEIntegration, QSEPermission, QSEProvider


async def get_qse_integration_by_project_id(
    *,
    db: AsyncSession,
    project_id: UUID,
) -> QSEIntegration | None:
    """Get QSE integration by project ID

        Parameters:
        -----------
        db: AsyncSession
            The database session.
        project_id: UUID
            The project ID to filter by.

        Returns:
        --------
        QSEIntegration | None
            The QSE integration if it exists, None otherwise.

    Args:
        db: Async session for operational data.
        project_id: Project id to fetch integration for.
    """
    query = (
        select(QSEIntegration)
        .options(
            contains_eager(QSEIntegration.qse_provider).load_only(
                QSEProvider.qse_provider_id,
                QSEProvider.name_short,
                QSEProvider.name_long,
            )
        )
        .join(
            QSEProvider,
            QSEIntegration.qse_provider_id == QSEProvider.qse_provider_id,
        )
        .where(QSEIntegration.project_id == project_id)
    )

    result = await db.execute(query)
    return result.scalar_one_or_none()


def get_qse_permissions_by_company_id(
    *,
    company_id: UUID,
) -> DbQuery[QSEPermission, Literal[False]]:
    """Build a query for QSE permissions by company id.

    Args:
        company_id: Company id to filter permissions by.
    """
    query = select(QSEPermission).where(QSEPermission.company_id == company_id)
    return DbQuery(query=query)


async def get_qse_fields_by_provider_id(
    *,
    db: AsyncSession,
    provider_id: int,
) -> list[QSEField]:
    """Fetch QSE provider fields for a given provider id.

    Args:
        db: Async session for operational data.
        provider_id: QSE provider id to filter fields by.
    """
    query = select(QSEField).where(QSEField.qse_provider_id == provider_id)
    result = await db.execute(query)
    return list(result.scalars().all())
