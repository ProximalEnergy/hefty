from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

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
        db: TODO: describe.
        project_id: TODO: describe.
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


async def get_qse_permissions_by_company_id(
    *,
    db: AsyncSession,
    company_id: UUID,
) -> list[QSEPermission]:
    """TODO: add description.

    Args:
        db: TODO: describe.
        company_id: TODO: describe.
    """
    query = select(QSEPermission).where(QSEPermission.company_id == company_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_qse_fields_by_provider_id(
    *,
    db: AsyncSession,
    provider_id: int,
) -> list[QSEField]:
    """TODO: add description.

    Args:
        db: TODO: describe.
        provider_id: TODO: describe.
    """
    query = select(QSEField).where(QSEField.qse_provider_id == provider_id)
    result = await db.execute(query)
    return list(result.scalars().all())
