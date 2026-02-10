import datetime
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends

from app import dependencies, utils
from core import models

router = APIRouter(prefix="/trackers", tags=["trackers"])


@router.get("/tracking-angles")
def get_tracking_angles(
    start: datetime.datetime,
    end: datetime.datetime,
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    _auth: None = Depends(dependencies.check_project_access_from_query_async),
):
    # Convert to project timezone
    """Return tracker angle time series for the project.

    Args:
        start: Naive start time for the window, assumed to be in UTC.
        end: Naive end time for the window, assumed to be in UTC.
        project: Project used for location and time zone context.
        _auth: Authorization dependency (unused).
    """
    start = pd.to_datetime(start).tz_localize("UTC").tz_convert(project.time_zone)
    end = pd.to_datetime(end).tz_localize("UTC").tz_convert(project.time_zone)
    lon, lat = project.point.coordinates  # type: ignore
    site = utils.location.Location(lat, lon, tz=project.time_zone)

    # Get tracking angles dataframe
    df = utils.get_tracking_angles(
        site_location=site,
        start=start,
        end=end,
        freq="5min",
    )

    data = {
        "times": df.index.tolist(),
        "tracker_theta": df["tracker_theta"].tolist(),
    }

    return data
