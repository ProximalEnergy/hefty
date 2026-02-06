import datetime

import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from core import models


def get_project_data(
    *,
    db: Session,
    tag_ids: list[int],
    start: datetime.datetime,
    end: datetime.datetime,
    raw: bool = False,
):
    """Fetch project data for tags within a time range.

    Args:
        db: Database session.
        tag_ids: Tag IDs to fetch.
        start: Start timestamp (inclusive).
        end: End timestamp (exclusive).
        raw: When true, read from raw data table.
    """
    if raw:
        model = models.DataRaw
    else:
        model = models.Data  # type: ignore

    statement = select(model)
    statement = statement.where(model.tag_id.in_(tag_ids))
    statement = statement.where(model.time >= start)
    statement = statement.where(model.time < end)

    return db.execute(statement).scalars().all()


def get_project_data_latest(
    *,
    project_db: Session,
    project_name_short: str,
    tag_ids: list[int],
    start: pd.Timestamp | datetime.datetime,
):
    """Fetch the latest data point per tag after a start time.

    Args:
        project_db: Project database session.
        project_name_short: Schema name for the project.
        tag_ids: Tag IDs to fetch.
        start: Only return rows after this timestamp.
    """
    statement = f"""
    (
        SELECT DISTINCT ON (tag_id)
            time as time_bucket,
            tag_id,
            value_continuous,
            value_boolean,
            value_cumulative,
            value_string,
            value_status
        FROM
            {project_name_short}.data
        WHERE
            time > :start and tag_id IN :tag_ids
        ORDER BY
            tag_id, time DESC
    );
    """

    query = project_db.execute(
        text(statement).bindparams(
            start=start.isoformat(),
            tag_ids=tuple(tag_ids),
        ),
    )

    return query.all()
