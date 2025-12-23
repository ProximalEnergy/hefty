from typing import Annotated
from uuid import UUID

import requests
from core.dependencies import get_db
from fastapi import APIRouter, Depends, HTTPException
from shapely.wkb import loads
from sqlalchemy.orm import Session

import core
from app import dependencies, settings

router = APIRouter(
    prefix="/{project_id}",
    tags=["gis"],
    dependencies=[Depends(dependencies.check_project_access_async)],
)


def _get_project_lat_lon(*, db: Session, project_id: UUID) -> tuple[float, float]:
    """Return latitude and longitude for a project point.

    Args:
        db: Database session to query project data.
        project_id: Project UUID used to look up coordinates.
    """
    project_data = core.crud.operational.projects.get_project(
        db=db,
        project_id=project_id,
        deep=True,
    ).model()
    wkb_bytes = bytes.fromhex(str(project_data.point))
    point = loads(wkb_bytes)
    return point.y, point.x


@router.get("/project-weather")
def get_project_weather(
    *,
    project_id: UUID,
    db: Annotated[Session, Depends(get_db)],
):
    """Fetch current weather data for the project's coordinates.

    Args:
        project_id: Project UUID used to look up coordinates.
        db: Database session dependency.
    """
    lat, lon = _get_project_lat_lon(db=db, project_id=project_id)
    weather_api_key = settings.WEATHER_API_KEY
    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&appid={weather_api_key}&units=imperial"
    )
    res = requests.get(url)
    if not res.ok:
        raise HTTPException(res.json()["cod"], res.json()["message"])
    data = res.json()
    return data


@router.get("/project-weather-forecast")
def get_project_weather_forecast(
    *,
    project_id: UUID,
    db: Annotated[Session, Depends(get_db)],
):
    """Fetch forecast weather data for the project's coordinates.

    Args:
        project_id: Project UUID used to look up coordinates.
        db: Database session dependency.
    """
    lat, lon = _get_project_lat_lon(db=db, project_id=project_id)
    weather_api_key = settings.WEATHER_API_KEY
    url = (
        "https://api.openweathermap.org/data/2.5/forecast"
        f"?lat={lat}&lon={lon}&appid={weather_api_key}&units=imperial"
    )
    res = requests.get(url)
    if not res.ok:
        raise HTTPException(res.json()["cod"], res.json()["message"])
    data = res.json()
    return data
