import datetime

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session


def get_project_data_raw(
    project_db: Session,
    *,
    project_name_short: str,
    tag_ids: list[int],
    start: pd.Timestamp,
    end: pd.Timestamp,
    interval: str,
):
    statement = f"""
    SELECT
        time_bucket(:interval, time) + interval :interval as time_bucket,
        tag_id,
        last(value_continuous, time) as value_continuous,
        last(value_boolean, time) as value_boolean,
        last(value_cumulative, time) as value_cumulative,
        last(value_string, time) as value_string,
        last(value_status, time) as value_status
    FROM
        {project_name_short}.data_raw
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


def get_project_data_raw_last(
    project_db: Session,
    *,
    project_name_short: str,
    tag_ids: list[int],
    start: pd.Timestamp,
    end: pd.Timestamp,
):
    statement = f"""
    (
        SELECT DISTINCT ON (tag_id)
            :end as time_bucket,
            tag_id,
            value_continuous,
            value_boolean,
            value_cumulative,
            value_string,
            value_status
        FROM
            {project_name_short}.data_raw
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


def get_project_data_raw_latest(
    project_db: Session,
    *,
    project_name_short: str,
    tag_ids: list[int],
    start: pd.Timestamp | datetime.datetime,
):
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
            {project_name_short}.data_raw
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


### END data_raw ###
