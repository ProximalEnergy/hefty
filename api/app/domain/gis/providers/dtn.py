from datetime import timedelta

import httpx
import shapely.geometry
from app.domain.gis.map import ArcGISProvider, MapData, MapDataProvider, MapDataType


class DTN(
    MapDataProvider,
    ArcGISProvider,
):
    """Specialized provider for hail and precipitation data"""

    arcgis_token_url = "https://arcgis.dtn.com/portal/sharing/rest/generateToken"  # noqa
    arcgis_endpoint_url = (
        "https://arcgis.dtn.com/feature/rest/services/Severe/"
        "StormPredictionCenterOutlook_US/FeatureServer"
    )

    async def _get_data(
        self,
        *,
        data_type: MapDataType,
        time_span: timedelta | None = None,
    ):
        """Load map data for the requested DTN data type.

        Args:
            data_type: Map data type to retrieve.
            time_span: Optional time span filter for the request.
        """
        match data_type:
            case MapDataType.HAIL_FORECAST_POLYGON:
                match time_span:
                    case timedelta(days=1):
                        arcgis_layer_id = 1
                    case timedelta(days=2):
                        arcgis_layer_id = 5
                    case _:
                        raise ValueError(
                            f"Invalid time span {time_span}"
                            " for hail forecast polygon data"
                            " only 1, 2, or 3 days are supported"
                        )

                polygons = await self.get_hail_forecast_polygons(
                    arcgis_layer_id=arcgis_layer_id
                )
                # Cast to the expected union type
                data_list = list[shapely.geometry.Polygon | shapely.geometry.Point](
                    polygons
                )
                return MapData(type=data_type, time_span=time_span, data=data_list)
            case _:
                raise NotImplementedError(f"Data type {data_type} not supported")

    async def get_hail_forecast_polygons(
        self,
        *,
        arcgis_layer_id: int,
    ):
        """Get hail forecast polygon data from the ArcGIS REST API.

        Args:
            arcgis_layer_id: ArcGIS layer ID to query.
        """

        # Get the authentication token
        token = await self.arcgis_token()

        # Build the query URL
        query_url = f"{self.arcgis_endpoint_url}/{arcgis_layer_id}/query"

        # Set up query parameters based on DTN example
        params = {
            "where": "1=1",  # Get all records
            "outFields": "*",  # Get all fields
            "returnGeometry": "true",
            "geometryPrecision": "3",
            "f": "json",
            "token": token,
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(query_url, params=params)

            if response.status_code == 200:
                data = response.json()

                # Check for errors in the response
                if "error" in data:
                    error_msg = data["error"].get("message", "Unknown error")
                    if data["error"]["code"] == 403:
                        raise PermissionError(f"Permission Denied: {error_msg}")
                    if data["error"]["code"] in [498, 499]:
                        # Token expired, refresh and retry
                        self.refresh_token()
                        token = await self.arcgis_token()
                        params["token"] = token

                        # Retry the request
                        retry_response = await client.get(query_url, params=params)
                        if retry_response.status_code == 200:
                            retry_data = retry_response.json()
                            return self._parse_polygons_response(data=retry_data)
                        else:
                            raise ValueError(
                                f"Request failed after token refresh: "
                                f"{retry_response.status_code}"
                            )
                    else:
                        raise Exception(f"Error: {error_msg}")

                return self._parse_polygons_response(data=data)

            else:
                raise ValueError(
                    f"Request failed with status code: {response.status_code}"
                )

    def _parse_polygons_response(self, *, data: dict) -> list[shapely.geometry.Polygon]:
        """Parse an ArcGIS response and extract polygons.

        Args:
            data: ArcGIS JSON response payload.
        """
        if "error" in data:
            error_msg = data["error"].get("message", "Unknown error")
            raise ValueError(f"ArcGIS API error: {error_msg}")

        polygons = []
        features = data.get("features", [])

        for feature in features:
            geometry = feature.get("geometry")
            if geometry and geometry.get("rings"):
                rings = geometry["rings"]
                if rings:
                    exterior = rings[0]
                    holes = rings[1:] if len(rings) > 1 else None

                    try:
                        polygon = shapely.geometry.Polygon(exterior, holes)
                        if polygon.is_valid:
                            polygons.append(polygon)
                    except Exception:
                        continue

        return polygons
