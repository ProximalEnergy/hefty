from typing import Literal

import sqlalchemy as sa

from core import models
from core.db_query import DbQuery


def get_project_cmms_tickets(
    *,
    cmms_ticket_ids: list[int] | None = None,
    cmms_integration_ids: list[int] | None = None,
    device_ids: list[int] | None = None,
    device_type_ids: list[int] | None = None,
    max_results: int | None = None,
    include_json_raw: bool = False,
) -> DbQuery[models.CMMSTicket, Literal[False]]:
    """
    Get the CMMS tickets for a project.

    Args:
        cmms_ticket_ids: The list of CMMS ticket ids to filter by.
        cmms_integration_ids: The list of CMMS integration ids to filter by.
        device_ids: The list of device ids to filter by.
        device_type_ids: The list of device type ids to filter by.
    """
    ticket = models.CMMSTicket
    cmms_device = models.CMMSDevice
    device = models.Device

    stmt = sa.select(ticket)

    if cmms_ticket_ids:
        stmt = stmt.where(ticket.cmms_ticket_id.in_(cmms_ticket_ids))

    if cmms_integration_ids:
        stmt = stmt.where(ticket.cmms_integration_id.in_(cmms_integration_ids))

    if device_ids or device_type_ids:
        stmt = stmt.join(
            cmms_device,
            sa.and_(
                ticket.cmms_device_id == cmms_device.cmms_device_id,
                ticket.cmms_integration_id == cmms_device.cmms_integration_id,
            ),
        ).join(device, cmms_device.device_id == device.device_id)

        if device_ids:
            stmt = stmt.where(device.device_id.in_(device_ids))

        if device_type_ids:
            stmt = stmt.where(device.device_type_id.in_(device_type_ids))

    if max_results:
        stmt = stmt.order_by(
            sa.func.coalesce(
                ticket.source_created_at,
                ticket.db_created_at,
            ).desc()
        ).limit(max_results)

    if not include_json_raw:
        stmt = stmt.options(sa.orm.defer(ticket.json_raw))

    return DbQuery(query=stmt)
