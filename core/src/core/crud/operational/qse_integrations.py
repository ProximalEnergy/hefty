from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from core.models import QSEField, QSEIntegration, QSEPermission, QSEProvider, User


async def get_qse_integration_by_project_id(
    *,
    db: AsyncSession,
    user: User,
    project_id: UUID,
    can_view: bool = True,
) -> tuple[QSEIntegration | None, bool]:
    """
    Get QSE integration by project ID, but only if the user's company has
    permission to view it.

    This function first checks if the integration exists, then checks if the
    user's company has permission to view it.

    Parameters:
    -----------
    db: AsyncSession
        The database session.
    user: User
        The user making the request.
    project_id: UUID
        The project ID to filter by.
    can_view: bool
        Whether to filter by view permissions (default: True).

    Returns:
    --------
    tuple[QSEIntegration | None, bool]
        A tuple of (integration, has_permission).
        - (None, True) if no integration exists for the project (404 case)
        - (integration, False) if integration exists but no permission (403 case)
        - (integration, True) if integration exists and user has permission
    """
    # First check if the integration exists at all (without permission check)
    existence_query = (
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

    existence_result = await db.execute(existence_query)
    integration = existence_result.scalar_one_or_none()

    # If no integration exists, return None with has_permission=True (404 case)
    if integration is None:
        return (None, True)

    # Integration exists, now check if user has permission
    permission_query = select(QSEPermission).where(
        QSEPermission.qse_integration_id == integration.qse_integration_id,
        QSEPermission.company_id == user.company_id,
        QSEPermission.can_view == can_view,
    )

    permission_result = await db.execute(permission_query)
    permission = permission_result.scalar_one_or_none()

    # If no permission exists, return integration with has_permission=False (403 case)
    if permission is None:
        return (integration, False)

    # User has permission, return the integration
    return (integration, True)


async def get_qse_fields_by_provider_id(
    *,
    db: AsyncSession,
    provider_id: int,
) -> list[QSEField]:
    query = select(QSEField).where(QSEField.qse_provider_id == provider_id)
    result = await db.execute(query)
    return list(result.scalars().all())
