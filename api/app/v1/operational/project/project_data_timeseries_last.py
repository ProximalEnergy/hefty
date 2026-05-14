from typing import Annotated

import pandas as pd
from core.crud.project import data_timeseries_last as project_data_timeseries_last
from core.db_query import OutputType
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import utils
from app.dependencies import get_project_db

router = APIRouter(
    prefix="/data-timeseries-last",
    tags=["project_data_timeseries_last"],
)


@router.get("")
async def get_data_timeseries_last_route(
    project_db: Annotated[Session, Depends(get_project_db)],
    tag_ids: Annotated[list[int] | None, Query()] = None,
    device_type_ids: Annotated[list[int] | None, Query()] = None,
    sensor_type_ids: Annotated[list[int] | None, Query()] = None,
    device_ids: Annotated[list[int] | None, Query()] = None,
    include_ghost_tags: Annotated[bool, Query()] = False,
):
    """Fetch the latest timeseries data with optional filters and unit scaling.

    Args:
        project_db: Project database session.
        tag_ids: Optional tag ids to filter by.
        device_type_ids: Optional device type ids to filter by.
        sensor_type_ids: Optional sensor type ids to filter by.
        device_ids: Optional device ids to filter by.
        include_ghost_tags: Include tags without sensor_type_id when True.
    """
    project_schema = utils.get_project_schema(project_db=project_db)
    df = await project_data_timeseries_last.get_data_timeseries_last(
        tag_ids=tag_ids,
        device_type_ids=device_type_ids,
        sensor_type_ids=sensor_type_ids,
        device_ids=device_ids,
        include_ghost_tags=include_ghost_tags,
        deep=True,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    if df.empty:
        return []

    # Perform unit scale and offset transformations
    scale = pd.to_numeric(df["unit_scale"], errors="coerce").fillna(1.0)
    offset = pd.to_numeric(df["unit_offset"], errors="coerce").fillna(0.0)

    for col in ["value_integer", "value_bigint", "value_real", "value_double"]:
        if col in df.columns:
            df[col] = df[col] * scale + offset

    # Return only the DataTimeseriesLast columns
    cols_to_return = [
        "tag_id",
        "time",
        "value_integer",
        "value_bigint",
        "value_real",
        "value_double",
        "value_boolean",
        "value_text",
    ]
    # Filter only columns that actually exist in the dataframe
    cols_to_return = [c for c in cols_to_return if c in df.columns]

    return df[cols_to_return].to_dict(orient="records")
