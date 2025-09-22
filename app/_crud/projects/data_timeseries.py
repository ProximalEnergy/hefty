import datetime

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session


def get_project_data_timeseries(
    project_db: Session,
    project_name_short: str,
    tag_ids: list[int],
    start: pd.Timestamp,
    end: pd.Timestamp,
    interval: str,
    *,
    cagg_interval: str | None = None,
):
    if cagg_interval:
        table_name = f"{project_name_short}.data_timeseries_{cagg_interval}"
    else:
        table_name = f"{project_name_short}.data_timeseries"

    statement = f"""
    SELECT
        time_bucket(:interval, time) + interval :interval as time_bucket,
        tag_id,
        last(value_integer, time) as value_integer,
        last(value_bigint, time) as value_bigint,
        last(value_real, time) as value_real,
        last(value_double, time) as value_double,
        last(value_boolean, time) as value_boolean,
        last(value_text, time) as value_text
    FROM
        {table_name}
    WHERE
        time >= :start and time < :end and tag_id IN :tag_ids
    GROUP BY
        time_bucket, tag_id
    ORDER BY
        time_bucket, tag_id;
    """

    query = project_db.execute(
        text(statement).bindparams(
            interval=interval,
            start=start.isoformat(),
            end=end.isoformat(),
            tag_ids=tuple(tag_ids),
        ),
    )

    return query.all()


def get_project_data_timeseries_last(
    project_db: Session,
    project_name_short: str,
    tag_ids: list[int],
    start: pd.Timestamp,
    end: pd.Timestamp,
    *,
    cagg_interval: str | None = None,
):
    if cagg_interval:
        table_name = f"{project_name_short}.data_timeseries_{cagg_interval}"
    else:
        table_name = f"{project_name_short}.data_timeseries"

    statement = f"""
    (
        SELECT DISTINCT ON (tag_id)
            :end as time_bucket,
            tag_id,
            value_integer,
            value_bigint,
            value_real,
            value_double,
            value_boolean,
            value_text
        FROM
            {table_name}
        WHERE
            time > :start and time <= :end and tag_id IN :tag_ids
        ORDER BY
            tag_id, time DESC
    );
    """

    query = project_db.execute(
        text(statement).bindparams(
            start=start.isoformat(),
            end=end.isoformat(),
            tag_ids=tuple(tag_ids),
        ),
    )

    return query.all()


def get_project_data_timeseries_latest(
    project_db: Session,
    project_name_short: str,
    tag_ids: list[int],
    start: pd.Timestamp | datetime.datetime,
    *,
    cagg_interval: str | None = None,
):
    if cagg_interval:
        table_name = f"{project_name_short}.data_timeseries_{cagg_interval}"
    else:
        table_name = f"{project_name_short}.data_timeseries"

    statement = f"""
    (
        SELECT DISTINCT ON (tag_id)
            time as time_bucket,
            tag_id,
            value_integer,
            value_bigint,
            value_real,
            value_double,
            value_boolean,
            value_text
        FROM
            {table_name}
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
