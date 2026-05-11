import datetime
from typing import Annotated
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends

from app import dependencies, interfaces, utils
from app._dependencies import authentication, authorization
from core import models

router = APIRouter(prefix="/trackers", tags=["trackers"])


async def require_tracking_angles_project_access(
    *,
    project_id: UUID,
    user: interfaces.UserAuthed = Depends(authentication.get_user),
) -> None:
    """Require project access for tracking angle requests.

    Args:
        project_id: Project UUID from the request.
        user: Authenticated user context.
    """
    await authorization.require_user_project(project_id=project_id, user=user)


@router.get("/tracking-angles")
def get_tracking_angles_route(
    start: datetime.datetime,
    end: datetime.datetime,
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
    _auth: None = Depends(require_tracking_angles_project_access),
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
