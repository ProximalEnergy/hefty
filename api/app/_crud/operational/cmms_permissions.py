from collections.abc import Sequence
from uuid import UUID

from core.models import CMMSIntegration, CMMSPermission
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager


async def get_cmms_permissions_by_project_id(
    *,
    db: AsyncSession,
    company_id: UUID,
    project_id: UUID,
    can_view: bool | None = True,
) -> Sequence[CMMSPermission]:
    """Used for pulling ticket information for a specific project assuming the
        user has view permissions.
        This function is an inner join on the CMMSPermission, CMMSIntegration,
        and CMMSProvider tables and will
        only return value where rows from all 3 tables are present. Data is
        filtered by the company_id and project_id,
        and optionally filtered by can_view (set to True in ticket pull function).

        Parameters:
        -----------
        db: AsyncSession
            The database session.
        company_id: UUID
            The company id.
        project_id: UUID
            The project id.
        can_view: Optional[bool]
            Whether the user has view permissions. If not provided, the value
            can be True/False/NULl, but
            there still must be a corresponding row in the CMMSPermission table.

        Returns:
        --------
        List of CMMSPermission objects.

    Args:
        db: TODO: describe.
        company_id: TODO: describe.
        project_id: TODO: describe.
        can_view: TODO: describe.
    """

    query = (
        select(CMMSPermission)
        .join(CMMSPermission.cmms_integration)
        # the contains_eager is used to preload the cmms_integration relationship
        # while allowing the query to be filtered off of the CMMSIntegration table
        .options(
            contains_eager(CMMSPermission.cmms_integration).joinedload(
                CMMSIntegration.cmms_provider
            )
        )
        .where(
            CMMSPermission.company_id == company_id,
            CMMSIntegration.project_id == project_id,
        )
    )
    if can_view is not None:
        query = query.where(CMMSPermission.can_view == can_view)

    result = await db.execute(query)
    return result.scalars().all()
