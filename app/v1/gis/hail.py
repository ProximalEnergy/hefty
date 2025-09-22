import json
from datetime import timedelta
from typing import Annotated

import shapely
from fastapi import APIRouter, HTTPException, Query

from app.core.gis.map import MapData, MapDataType
from app.core.gis.providers.dtn import DTN

router = APIRouter(tags=["gis"])


@router.get(
    "/hail-forecast-polygons",
    summary="Get DTN hail forecast polygons",
    description="Query DTN ArcGIS service for hail forecast polygon data",
)
async def get_hail_forecast_polygons(
    days: Annotated[int, Query(description="Forecast days (1 or 2)", ge=1, le=2)] = 1,
):
    """
    Get hail forecast polygons from DTN ArcGIS service.

    Args:
        days: Number of days for forecast (1 or 2)

    Returns:
        HailForecastPolygonResponse: Polygon data with metadata

    Raises:
        HTTPException: If service is unavailable or authentication fails
    """
    try:
        # Initialize DTN provider
        dtn_provider = DTN()

        # Query for hail forecast data
        time_span = timedelta(days=days)
        map_data = await dtn_provider.get_data(
            data_type=MapDataType.HAIL_FORECAST_POLYGON,
            time_span=time_span,
        )

        if not map_data or not map_data.data:
            return MapData(
                type=MapDataType.HAIL_FORECAST_POLYGON,
                time_span=time_span,
                data=[],
            )

        # Convert Shapely polygons to GeoJSON-like format
        polygons = []
        for i, polygon in enumerate(map_data.data):
            polygon_dict = {
                "id": i,
                "geometry": json.loads(shapely.to_geojson(polygon)),
            }
            polygons.append(polygon_dict)

        return MapData(
            type=MapDataType.HAIL_FORECAST_POLYGON,
            time_span=time_span,
            data=polygons,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=422, detail=f"Invalid request parameters: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f" {str(e)}")
