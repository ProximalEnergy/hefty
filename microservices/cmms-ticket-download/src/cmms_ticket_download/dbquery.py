from typing import Any, Literal, cast

import sqlalchemy as sa
from core.database import with_db
from core.db_query import DbQuery
from core.enumerations import OutputType
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload

from core import models


def get_cmms_integration_with_project_query(
    *, cmms_integration_id: int
) -> DbQuery[sa.Row[tuple[models.CMMSIntegration, models.Project]], Literal[False]]:
    """Build a query for a CMMS integration and its project.

    Args:
        cmms_integration_id: CMMS integration ID to load.
    """

    stmt = (
        sa.select(models.CMMSIntegration, models.Project)
        .join(
            models.Project,
            models.CMMSIntegration.project_id == models.Project.project_id,
        )
        .options(selectinload(models.CMMSIntegration.cmms_provider))
        .where(models.CMMSIntegration.cmms_integration_id == cmms_integration_id)
    )
    return DbQuery(query=stmt)


def get_cmms_integration_with_project(
    *, cmms_integration_id: int
) -> tuple[models.CMMSIntegration, models.Project]:
    """Get a CMMS integration and its project from the operational schema.

    Args:
        cmms_integration_id: CMMS integration ID to load.
    """

    result = get_cmms_integration_with_project_query(
        cmms_integration_id=cmms_integration_id
    ).get(schema=None, output_type=OutputType.SQLALCHEMY)
    rows = cast(list[Any], result)
    if not rows:
        raise ValueError(f"CMMS integration {cmms_integration_id} was not found")
    cmms_integration, project = rows[0]
    return cmms_integration, project


def bulk_upsert_cmms_tickets_query(
    *, tickets_data: list[dict[str, Any]]
) -> DbQuery[Any, Literal[False]]:
    """Build a query to upsert CMMS tickets.

    Args:
        tickets_data: CMMS ticket rows to insert or update.
    """

    insert_stmt = pg_insert(models.CMMSTicket).values(tickets_data)
    update_dict = {
        c.name: c
        for c in insert_stmt.excluded
        if c.name not in ("cmms_ticket_id", "db_created_at")
    }
    upsert_stmt = insert_stmt.on_conflict_do_update(
        index_elements=["cmms_integration_id", "source_id"],
        set_=update_dict,
    )
    return DbQuery(query=upsert_stmt)


def execute_bulk_upsert_cmms_tickets(
    *, schema: str, tickets_data: list[dict[str, Any]]
) -> int:
    """Upsert CMMS tickets into a project schema.

    Args:
        schema: Project schema to write into.
        tickets_data: CMMS ticket rows to insert or update.
    """

    if not tickets_data:
        return 0

    with with_db(schema=schema) as db:
        bulk_upsert_cmms_tickets_query(tickets_data=tickets_data).execute(executor=db)
        db.commit()

    return len(tickets_data)
