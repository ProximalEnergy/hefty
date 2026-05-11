from uuid import UUID

import httpx
from core.db_query import OutputType
from fastapi import APIRouter, Depends, HTTPException
from shapely.wkb import loads

from app import settings
from app._dependencies import authorization
from core import crud, models

router = APIRouter(
    prefix="/{project_id}",
    tags=["gis"],
    dependencies=[Depends(authorization.require_user_project)],
)


async def _get_project_lat_lon(*, project_id: UUID) -> tuple[float, float]:
    """Return latitude and longitude for a project point.

    Args:
        project_id: Project UUID used to look up coordinates.
    """
    project_query = crud.operational.projects.get_project(
        project_id=project_id,
        columns=(models.Project.point,),
    )
    project_data = await project_query.get_async(
        output_type=OutputType.SQLALCHEMY,
    )
    if not project_data:
        raise HTTPException(status_code=404, detail="Project not found")
    wkb_bytes = bytes.fromhex(str(project_data.point))
    point = loads(wkb_bytes)
    return point.y, point.x


@router.get("/project-weather")
async def get_project_weather(
    *,
    project_id: UUID,
):
    """Fetch current weather data for the project's coordinates.

    Args:
        project_id: Project UUID used to look up coordinates.
    """
    lat, lon = await _get_project_lat_lon(project_id=project_id)
    weather_api_key = settings.WEATHER_API_KEY
    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&appid={weather_api_key}&units=imperial"
    )
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
    if not res.is_success:
        data = res.json()
        raise HTTPException(
            status_code=int(data.get("cod", res.status_code)),
            detail=data.get("message", "Weather API request failed"),
        )
    return res.json()


@router.get("/project-weather-forecast")
async def get_project_weather_forecast(
    *,
    project_id: UUID,
):
    """Fetch forecast weather data for the project's coordinates.

    Args:
        project_id: Project UUID used to look up coordinates.
    """
    lat, lon = await _get_project_lat_lon(project_id=project_id)
    weather_api_key = settings.WEATHER_API_KEY
    url = (
        "https://api.openweathermap.org/data/2.5/forecast"
        f"?lat={lat}&lon={lon}&appid={weather_api_key}&units=imperial"
    )
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
    if not res.is_success:
        data = res.json()
        raise HTTPException(
            status_code=int(data.get("cod", res.status_code)),
            detail=data.get("message", "Weather API request failed"),
        )
    return res.json()
