import datetime
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse
from pvlib import location
from pydantic import BaseModel

from app.dependencies import get_project_api
from core import models

router = APIRouter(
    prefix="/solar",
    tags=["project_solar"],
)


class SolarPositionResponse(BaseModel):
    """Solar position information for a project."""

    elevation_angle: float
    azimuth: float
    is_daytime: bool
    next_sunrise: datetime.datetime | None


@router.get(
    "/position", response_model=SolarPositionResponse, response_class=ORJSONResponse
)
def get_solar_position(
    project: Annotated[models.Project, Depends(get_project_api)],
    timestamp: datetime.datetime | None = None,
):
    """Get current solar position and related information for a project.

    Args:
        project: The project to get solar position for.
        timestamp: Optional timestamp to calculate solar position for.
                   If not provided, uses current time in project timezone.

    Returns:
        SolarPositionResponse: Solar position data including elevation, azimuth,
                              daytime status, and next sunrise time.
    """
    # Get project location
    lon, lat = project.point.coordinates  # type: ignore
    site = location.Location(lat, lon, tz=project.time_zone)

    # Use provided timestamp or current time in project timezone
    if timestamp is None:
        now = pd.Timestamp.now(tz=project.time_zone)
    else:
        # Convert to project timezone if needed
        if timestamp.tzinfo is None:
            now = (
                pd.to_datetime(timestamp)
                .tz_localize("UTC")
                .tz_convert(project.time_zone)
            )
        else:
            now = pd.to_datetime(timestamp).tz_convert(project.time_zone)

    # Get current solar position
    solpos = site.get_solarposition(now)
    elevation = float(solpos["elevation"].iloc[0])
    azimuth = float(solpos["azimuth"].iloc[0])

    # Determine if it's daytime (elevation > 0)
    is_daytime = elevation > 0

    # Calculate next sunrise
    next_sunrise = None
    if not is_daytime:
        # If it's nighttime, find next sunrise
        # First check hourly for the next 48 hours to find the day
        start_time = now
    else:
        # If it's daytime, find next sunrise (tomorrow)
        # Start from tomorrow at midnight
        start_time = (now.normalize() + pd.Timedelta(days=1)).tz_localize(None)
        start_time = pd.Timestamp(start_time).tz_localize(project.time_zone)

    # First pass: check hourly to find the approximate sunrise hour
    hourly_times = pd.date_range(
        start=start_time,
        periods=48,  # 48 hours
        freq="1h",
        tz=project.time_zone,
    )
    hourly_solpos = site.get_solarposition(hourly_times)
    hourly_elevations = hourly_solpos["elevation"]

    # Find first hour when elevation becomes positive
    positive_hours = hourly_elevations[hourly_elevations > 0]
    if len(positive_hours) > 0:
        sunrise_hour = positive_hours.index[0]
        # Second pass: check minute-by-minute in the hour before sunrise
        # to get more precise sunrise time
        minute_start = sunrise_hour - pd.Timedelta(hours=1)
        minute_times = pd.date_range(
            start=minute_start,
            periods=120,  # 2 hours * 60 minutes
            freq="1min",
            tz=project.time_zone,
        )
        minute_solpos = site.get_solarposition(minute_times)
        minute_elevations = minute_solpos["elevation"]

        # Find first minute when elevation becomes positive
        positive_minutes = minute_elevations[minute_elevations > 0]
        if len(positive_minutes) > 0:
            sunrise_time = positive_minutes.index[0]
            next_sunrise = sunrise_time.to_pydatetime()

    return SolarPositionResponse(
        elevation_angle=elevation,
        azimuth=azimuth,
        is_daytime=is_daytime,
        next_sunrise=next_sunrise,
    )
