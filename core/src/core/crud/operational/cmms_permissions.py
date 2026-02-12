from typing import Literal
from uuid import UUID

import sqlalchemy as sa

from core import models
from core.db_query import DbQuery


def get_cmms_permissions_by_project_id(
    *,
    company_id: UUID,
    project_id: UUID,
    can_view: bool | None = True,
) -> DbQuery[sa.Row[tuple[models.CMMSPermission, str]], Literal[False]]:
    """
    Get the CMMS permissions for a project.

    Args:
        company_id: The company id.
        project_id: The project id.
        can_view: Whether the user can view the CMMS permissions.

    Returns:
        A DbQuery object containing the CMMS permissions.
    """

    perm = models.CMMSPermission
    inte = models.CMMSIntegration
    prov = models.CMMSProvider

    provider_name = prov.name_long.label("cmms_provider_name_long")

    stmt = (
        sa.select(perm, provider_name)
        .join(inte, perm.cmms_integration_id == inte.cmms_integration_id)
        .join(prov, inte.cmms_provider_id == prov.cmms_provider_id)
        .where(
            perm.company_id == company_id,
            inte.project_id == project_id,
        )
    )

    if can_view is not None:
        stmt = stmt.where(perm.can_view == can_view)

    return DbQuery(query=stmt)
