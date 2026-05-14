from typing import Literal

import sqlalchemy as sa
from core.db_query import DbQuery
from sqlalchemy.orm import joinedload

from core import models


def get_project_cmms_devices(
    *,
    cmms_integration_ids: list[int] | None = None,
    device_ids: list[int] | None = None,
) -> DbQuery[models.CMMSDevice, Literal[False]]:
    """Return CMMS devices for a project as a DbQuery.

    Args:
        cmms_integration_ids: Optional list of integration IDs to filter on.
        device_ids: Optional list of device IDs to narrow the CMMS devices.
    """
    stmt = sa.select(models.CMMSDevice).options(
        joinedload(models.CMMSDevice.device),
    )

    if cmms_integration_ids:
        stmt = stmt.where(
            models.CMMSDevice.cmms_integration_id.in_(cmms_integration_ids),
        )

    if device_ids:
        stmt = stmt.where(
            models.CMMSDevice.device_id.in_(device_ids),
        )

    return DbQuery(query=stmt)
