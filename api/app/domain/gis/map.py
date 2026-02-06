import datetime
from abc import ABC
from dataclasses import dataclass
from enum import StrEnum

import shapely

from app.domain.gis._utils.arcgis import get_arcgis_token


class MapDataType(StrEnum):
    """Identifiers for supported map data types."""

    HAIL_FORECAST_POLYGON = "hail_forecast_polygon"


@dataclass(slots=True)
class MapData:
    """
    Return type for all map data providers
    """

    type: MapDataType
    time_span: datetime.timedelta | None
    data: list[shapely.Polygon | shapely.Point]


class MapDataProvider(ABC):
    """Base class for map data providers"""

    async def get_data(
        self,
        *,
        data_type: MapDataType,
        time_span: datetime.timedelta | None,
    ) -> MapData | None:
        """Get map data for the given data type.

        Args:
            data_type: Map data type to fetch.
            time_span: Optional time span to filter data.
        """
        return await self._get_data(
            data_type=data_type,
            time_span=time_span,
        )

    async def _get_data(
        self,
        *,
        data_type: MapDataType,
        time_span: datetime.timedelta | None,
    ) -> MapData | None:
        """Get map data for the given data type.

        Args:
            data_type: Map data type to fetch.
            time_span: Optional time span to filter data.
        """
        raise NotImplementedError


class ArcGISProvider(ABC):
    """Mixin for providers that use ArcGIS services"""

    arcgis_token_url: str
    _arcgis_token: str | None = None

    async def arcgis_token(self) -> str:
        """Get or fetch the ArcGIS token"""
        if self._arcgis_token is None:
            self._arcgis_token = get_arcgis_token(provider=self)
        return self._arcgis_token

    def refresh_token(self) -> None:
        """Force refresh of the ArcGIS token"""
        self._arcgis_token = None
