import datetime
from collections.abc import Sequence
from uuid import UUID

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, defer

from core import models


def api_get_kpi_data(
    *,
    db: Session,
    start: datetime.date,
    end: datetime.date,
    project_ids: list[UUID] = [],
    kpi_type_ids: list[int] = [],
    include_device_data: bool = True,
):
    """
    Retrieve KPI data from the operational schema within a specified date range.

    Args:
        db (Session): The database session to use for the query.
        start (datetime.date): The start date for filtering the KPI data.
        end (datetime.date): The end date for filtering the KPI data.
        project_ids (list[UUID], optional): A list of project IDs to
            filter the KPI data. Defaults to an empty list.
        kpi_type_ids (list[int], optional): A list of KPI type IDs to
            filter the KPI data. Defaults to an empty list.
        include_device_data (bool, optional): A flag indicating whether
            to include device data in the query. Defaults to True.

    Returns:
        pd.DataFrame: A DataFrame containing the operational KPI data that
            matches the specified filters.
    """
    if include_device_data:
        statement = select(models.OperationalKPIData)
    else:
        statement = select(models.OperationalKPIData).options(
            defer(
                models.OperationalKPIData.device_data_json,
            ),  # Exclude this column from the SQL query
        )

    if project_ids:
        statement = statement.where(
            models.OperationalKPIData.project_id.in_(project_ids),
        )
    if kpi_type_ids:
        statement = statement.where(
            models.OperationalKPIData.kpi_type_id.in_(kpi_type_ids),
        )
    statement = statement.where(models.OperationalKPIData.date >= start)
    statement = statement.where(models.OperationalKPIData.date < end)

    # NOTE: This function returns a pandas DataFrame using read_sql
    # because of how SQLAlchemy handles the `defer` option.
    return pd.read_sql(
        statement,
        db.connection(),
    )


async def get_kpi_data_async(
    *,
    db: AsyncSession,
    start: datetime.date,
    end: datetime.date,
    project_ids: list[UUID] = [],
    kpi_type_ids: Sequence[int] = [],
    include_device_data: bool = True,
):
    """
    Retrieve KPI data from the operational schema within a specified date range.

    Args:
        db (AsyncSession): The database session to use for the query.
        start (datetime.date): The start date for filtering the KPI data.
        end (datetime.date): The end date for filtering the KPI data.
        project_ids (list[UUID], optional): A list of project IDs to
            filter the KPI data. Defaults to an empty list.
        kpi_type_ids (list[int], optional): A list of KPI type IDs to
            filter the KPI data. Defaults to an empty list.
        include_device_data (bool, optional): A flag indicating whether
            to include device data in the query. Defaults to True.

    Returns:
        pd.DataFrame: A DataFrame containing the operational KPI data that
            matches the specified filters.
    """
    if include_device_data:
        query = select(models.OperationalKPIData)
    else:
        query = select(models.OperationalKPIData).options(
            defer(
                models.OperationalKPIData.device_data_json,
            ),  # Exclude this column from the SQL query
        )

    if project_ids:
        query = query.where(models.OperationalKPIData.project_id.in_(project_ids))
    if kpi_type_ids:
        query = query.where(models.OperationalKPIData.kpi_type_id.in_(kpi_type_ids))
    query = query.where(models.OperationalKPIData.date >= start)
    query = query.where(models.OperationalKPIData.date < end)

    # Execute the query and get results
    result = await db.execute(query)
    records = result.scalars().all()

    # Convert to DataFrame
    if records:
        # Convert SQLAlchemy objects to dictionaries
        data = [record.__dict__ for record in records]
        # Remove SQLAlchemy internal state
        for record_dict in data:
            record_dict.pop("_sa_instance_state", None)
        return pd.DataFrame(data)
    else:
        return pd.DataFrame()
