import datetime
from typing import Annotated
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse

from app import dependencies, utils
from core import models

router = APIRouter(prefix="/trackers", tags=["trackers"])


@router.get("/tracking-angles", response_class=ORJSONResponse)
def get_tracking_angles(
    project_id: UUID,
    start: datetime.datetime,
    end: datetime.datetime,
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    _auth: None = Depends(dependencies.check_project_access_from_query_async),
):
    # Convert to project timezone
    """todo

    Args:
        project_id: TODO: describe.
        start: TODO: describe.
        end: TODO: describe.
        project: TODO: describe.
        _auth: TODO: describe.
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
