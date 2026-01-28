import datetime
from typing import Annotated

import pandas as pd
from app import dependencies, interfaces, logger
from app.utils import get_include_in_schema
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.db_query import OutputType
from core.enumerations import SensorType
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import core
from core import models

router = APIRouter(
    prefix="/combiner-swaps",
    tags=["combiner_swaps"],
    include_in_schema=get_include_in_schema(),
)


@router.get("/validate-combiner-data")
async def validate_combiner_data(
    start: datetime.datetime,
    end: datetime.datetime,
    device_ids: Annotated[list[int] | None, Query()] = None,
    project: models.Project = Depends(dependencies.get_project_api),
    project_db: Session = Depends(dependencies.get_project_db),
    user_data: interfaces.UserData = Depends(dependencies.get_user_data_async),  # noqa: ARG001
    _access: None = Depends(dependencies.check_project_access_async),
):
    """This function is used in combiner swaps functionality to figure out
        if there is enough good combiner data.

    Args:
        start: TODO: describe.
        end: TODO: describe.
        device_ids: TODO: describe.
        project: TODO: describe.
        project_db: TODO: describe.
        user_data: TODO: describe.
        _access: TODO: describe.
    """
    try:
        # Validate start and end times
        if start >= end:
            raise HTTPException(
                status_code=422,
                detail="Start time must be before end time",
            )

        # Get project timezone
        project_tz = project.time_zone

        # Convert device IDs to standard Python integers if needed
        if device_ids is None:
            device_ids = []
        combiner_device_ids = [int(x) for x in device_ids]

        # Get combiner current tags
        tags = await core.crud.project.tags.get_project_tags_v2(
            sensor_type_ids=[SensorType.PV_DC_COMBINER_CURRENT],
            device_ids=combiner_device_ids,
        ).get_async(
            schema=project.name_short,
            output_type=OutputType.POLARS,
        )

        if tags.is_empty():
            return {
                "isValid": False,
                "message": "No tags found for the specified device IDs",
            }
        # Get time series data
        try:
            data_timeseries_instance = await DataTimeseries(
                project_name_short=project.name_short,
                filter_method=FilterMethod.TAG_POLARS,
                filter_values=tags,
                query_start=start,
                query_end=end,
                project_db=project_db,
            ).get()

            df = data_timeseries_instance.df.to_pandas()
            df = df.set_index("time")
            df.index = pd.to_datetime(df.index).tz_convert(project.time_zone)
            df.columns = df.columns.astype(int)

        except Exception as e:
            return {
                "isValid": False,
                "message": (
                    f"No data available for specified time period."
                    f"Please choose a different time period."
                    f": {str(e)}",
                ),
            }

        if df.empty:
            return {
                "isValid": False,
                "message": "No data available for the specified time period",
            }

        # Convert to project timezone
        df.index = pd.to_datetime(df.index).tz_convert(project_tz)

        total_sum = df.sum(axis=1)
        total_sum_normalized = total_sum / total_sum.max()

        # Calculate rolling variability with centered window
        window = "30min"
        rolling_variability = (
            total_sum_normalized.diff().abs().rolling(window=window, center=True).sum()
        )

        # Calculate threshold (20% of max)
        threshold = rolling_variability.max() * 0.20

        # Find where the line crosses the threshold
        above_threshold = rolling_variability >= threshold
        crossings = above_threshold.diff()

        # Get all crossing points
        crossing_times = crossings[crossings != 0].index

        if len(crossing_times) >= 2:
            # Find first crossing upward and last crossing downward
            start_time = crossing_times[1]  # First crossing (going up)
            end_time = crossing_times[-1]  # Last crossing (going down)

            # Filter data between start and end time
            filtered_df = df[start_time:end_time]
        else:
            return {
                "isValid": False,
                "message": (
                    "This day has no high-variability windows. Select a different day!",
                ),
            }

        # Calculate duration in minutes
        duration_minutes = (
            filtered_df.index[-1] - filtered_df.index[0]
        ).total_seconds() / 60
        duration_threshold = 90
        if duration_minutes < duration_threshold:
            return {
                "isValid": False,
                "message": (
                    f"High-variability window too small."
                    f"Select a day with more clouds! "
                    f"Score: {duration_minutes:.0f} minutes "
                    f"(minimum required: {duration_threshold})",
                ),
            }

        mean_variability = rolling_variability[start_time:end_time].mean()
        variability_threshold = 0.6
        if mean_variability < variability_threshold:
            return {
                "isValid": False,
                "message": (
                    f"This day has too little variability. "
                    f"Select a day with more clouds! Score: {mean_variability:.2f} "
                    f"(minimum required: {variability_threshold})",
                ),
            }

        # Check for zeros
        zero_count = (filtered_df == 0).sum().sum()
        zero_threshold = 25
        if zero_count > zero_threshold:
            return {
                "isValid": False,
                "message": (
                    f"Too many zero values in data. "
                    f"Select a different day! Count: {zero_count} "
                    f"(maximum allowed: {zero_threshold})",
                ),
            }

        return {"isValid": True, "message": "Data validation successful"}

    except Exception as e:
        logger.logger.error(
            f"Error in validate_combiner_data: {str(e)}",
            exc_info=True,
        )  # Add exc_info=True
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
