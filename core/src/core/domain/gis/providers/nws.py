"""NWS (National Weather Service) provider for weather forecast polygons."""

import httpx
import shapely.geometry
from shapely.geometry import Point, Polygon


class NWSProvider:
    """Provider for NWS weather forecast polygons from NOAA ArcGIS services."""

    spc_wx_outlooks_endpoint = (
        "https://mapservices.weather.noaa.gov/vector/rest/services/"
        "outlooks/SPC_wx_outlks/MapServer"
    )
    spc_fire_wx_endpoint = (
        "https://mapservices.weather.noaa.gov/vector/rest/services/"
        "fire_weather/SPC_firewx/MapServer"
    )

    def get_tornado_outlook_polygons(self) -> list[tuple[Polygon, float, str]]:
        """Get tornado outlook polygons with probability values (Day 1 & Day 2).

        Args:
            None

        Returns:
            List of tuples (polygon, probability, day).
        """
        day1 = self._get_polygons_from_layer(
            endpoint_url=self.spc_wx_outlooks_endpoint, layer_id=3, day="day1"
        )
        day2 = self._get_polygons_from_layer(
            endpoint_url=self.spc_wx_outlooks_endpoint, layer_id=11, day="day2"
        )
        return [*day1, *day2]

    def get_wind_outlook_polygons(self) -> list[tuple[Polygon, float, str]]:
        """Get wind outlook polygons with probability values (Day 1 & Day 2).

        Args:
            None

        Returns:
            List of tuples (polygon, probability, day).
        """
        day1 = self._get_polygons_from_layer(
            endpoint_url=self.spc_wx_outlooks_endpoint, layer_id=7, day="day1"
        )
        day2 = self._get_polygons_from_layer(
            endpoint_url=self.spc_wx_outlooks_endpoint, layer_id=15, day="day2"
        )
        return [*day1, *day2]

    def get_fire_outlook_polygons(self) -> list[tuple[Polygon, int, str]]:
        """Get fire outlook polygons with severity codes (Day 1 & Day 2).

        Fire alerts use numeric codes: 5=Elevated, 8=Critical, 10=Extreme
        instead of probability percentages.

        Args:
            None

        Returns:
            List of tuples (polygon, severity_code, day).
        """
        day1 = self._get_fire_polygons_from_layer(
            endpoint_url=self.spc_fire_wx_endpoint, layer_id=1, day="day1"
        )
        day2 = self._get_fire_polygons_from_layer(
            endpoint_url=self.spc_fire_wx_endpoint, layer_id=4, day="day2"
        )
        return [*day1, *day2]

    def get_hail_outlook_polygons(self) -> list[tuple[Polygon, float, str]]:
        """Get hail outlook polygons with probability values (SPC day 1).

        Uses SPC outlooks hail layers:
        - Day 1: layer 5
        - Day 2: layer 13

        Args:
            None

        Returns:
            List of tuples (polygon, probability, day) where probability is the
            'dn' value.
        """
        day1 = self._get_polygons_from_layer(
            endpoint_url=self.spc_wx_outlooks_endpoint, layer_id=5, day="day1"
        )
        day2 = self._get_polygons_from_layer(
            endpoint_url=self.spc_wx_outlooks_endpoint, layer_id=13, day="day2"
        )
        return [*day1, *day2]

    def _get_polygons_from_layer(
        self, *, endpoint_url: str, layer_id: int, day: str
    ) -> list[tuple[Polygon, float, str]]:
        """Get polygons from an NWS ArcGIS layer.

        Args:
            endpoint_url: Base URL for the ArcGIS service.
            layer_id: Layer ID to query.
            day: Day label (e.g., "day1", "day2").

        Returns:
            List of tuples (polygon, probability, day) where probability is the
            'dn' value.
        """
        query_url = f"{endpoint_url}/{layer_id}/query"

        params = {
            "where": "1=1",
            "outFields": "dn",
            "returnGeometry": "true",
            "geometryPrecision": "3",
            "outSR": 4326,  # WGS84
            "f": "json",
        }

        # Use synchronous httpx to avoid async context conflicts
        response = httpx.get(query_url, params=params, timeout=30.0)  # type: ignore[arg-type]

        if response.status_code != 200:
            raise ValueError(f"Request failed with status code: {response.status_code}")

        data = response.json()

        if "error" in data:
            error_msg = data["error"].get("message", "Unknown error")
            raise ValueError(f"ArcGIS API error: {error_msg}")

        return self._parse_polygons_response(data=data, day=day)

    def _get_fire_polygons_from_layer(
        self, *, endpoint_url: str, layer_id: int, day: str
    ) -> list[tuple[Polygon, int, str]]:
        """Get fire polygons from an NWS ArcGIS layer.

        Fire alerts use numeric severity codes instead of probability percentages.

        Args:
            endpoint_url: Base URL for the ArcGIS service.
            layer_id: Layer ID to query.
            day: Day label (e.g., "day1", "day2").

        Returns:
            List of tuples (polygon, severity_code, day) where severity_code
            is the raw 'dn' value (5=Elevated, 8=Critical, 10=Extreme).
        """
        query_url = f"{endpoint_url}/{layer_id}/query"

        params = {
            "where": "1=1",
            "outFields": "dn",
            "returnGeometry": "true",
            "geometryPrecision": "3",
            "outSR": 4326,  # WGS84
            "f": "json",
        }

        # Use synchronous httpx to avoid async context conflicts
        response = httpx.get(query_url, params=params, timeout=30.0)  # type: ignore[arg-type]

        if response.status_code != 200:
            raise ValueError(f"Request failed with status code: {response.status_code}")

        data = response.json()

        if "error" in data:
            error_msg = data["error"].get("message", "Unknown error")
            raise ValueError(f"ArcGIS API error: {error_msg}")

        return self._parse_fire_polygons_response(data=data, day=day)

    def _calculate_winding_order(self, *, ring: list[list[float]]) -> bool:
        """Calculate if a ring is clockwise (exterior) or counter-clockwise (interior).

        Args:
            ring: List of [x, y] coordinate pairs.

        Returns:
            True if clockwise (exterior), False if counter-clockwise (interior).
        """
        if len(ring) < 3:
            return True  # Default to exterior for invalid rings

        sum_winding = 0.0
        for i in range(len(ring) - 1):
            x1, y1 = ring[i]
            x2, y2 = ring[i + 1]
            sum_winding += (x2 - x1) * (y2 + y1)

        return sum_winding > 0  # Clockwise = exterior ring

    def _parse_polygons_response(
        self, *, data: dict, day: str
    ) -> list[tuple[Polygon, float, str]]:
        """Parse ArcGIS response and extract polygons with probability values.

        ArcGIS features can contain multiple rings. Rings with clockwise winding
        order are exterior rings (separate polygons), while counter-clockwise
        rings are interior rings (holes in the last exterior ring).

        Args:
            data: JSON response from ArcGIS API.
            day: Day label (e.g., "day1", "day2").

        Returns:
            List of tuples (polygon, probability, day) where probability is the
            'dn' value.
        """
        polygons = []
        features = data.get("features", [])

        for feature in features:
            geometry = feature.get("geometry")
            attributes = feature.get("attributes", {})
            probability = attributes.get("dn", 0.0)

            if geometry and geometry.get("rings"):
                rings = geometry["rings"]
                if not rings:
                    continue

                # Group rings into polygons based on winding order
                polygon_rings = []  # List of [exterior, [holes...]]

                for ring in rings:
                    is_exterior = self._calculate_winding_order(ring=ring)

                    if is_exterior:
                        # Start new polygon with this exterior ring
                        polygon_rings.append([ring])
                    else:
                        # Add as hole to the last polygon
                        if polygon_rings:
                            polygon_rings[-1].append(ring)

                # Create Shapely Polygon objects
                for ring_group in polygon_rings:
                    if not ring_group:
                        continue

                    exterior = ring_group[0]
                    holes = ring_group[1:] if len(ring_group) > 1 else None

                    try:
                        polygon = shapely.geometry.Polygon(exterior, holes)
                        if polygon.is_valid:
                            polygons.append((polygon, float(probability), day))
                    except Exception:
                        continue

        return polygons

    def _parse_fire_polygons_response(
        self, *, data: dict, day: str
    ) -> list[tuple[Polygon, int, str]]:
        """Parse ArcGIS response and extract polygons with fire severity codes.

        ArcGIS features can contain multiple rings. Rings with clockwise winding
        order are exterior rings (separate polygons), while counter-clockwise
        rings are interior rings (holes in the last exterior ring).

        Args:
            data: JSON response from ArcGIS API.
            day: Day label (e.g., "day1", "day2").

        Returns:
            List of tuples (polygon, severity_code, day) where severity_code
            is the raw 'dn' value (5=Elevated, 8=Critical, 10=Extreme).
        """
        polygons = []
        features = data.get("features", [])

        for feature in features:
            geometry = feature.get("geometry")
            attributes = feature.get("attributes", {})
            severity_code = attributes.get("dn", 0)

            if geometry and geometry.get("rings") and severity_code:
                rings = geometry["rings"]
                if not rings:
                    continue

                # Group rings into polygons based on winding order
                polygon_rings = []  # List of [exterior, [holes...]]

                for ring in rings:
                    is_exterior = self._calculate_winding_order(ring=ring)

                    if is_exterior:
                        # Start new polygon with this exterior ring
                        polygon_rings.append([ring])
                    else:
                        # Add as hole to the last polygon
                        if polygon_rings:
                            polygon_rings[-1].append(ring)

                # Create Shapely Polygon objects
                for ring_group in polygon_rings:
                    if not ring_group:
                        continue

                    exterior = ring_group[0]
                    holes = ring_group[1:] if len(ring_group) > 1 else None

                    try:
                        polygon = shapely.geometry.Polygon(exterior, holes)
                        if polygon.is_valid:
                            polygons.append((polygon, int(severity_code), day))
                        else:
                            # Try to make the polygon valid
                            try:
                                valid_polygon = polygon.buffer(
                                    0
                                )  # This often fixes geometry issues
                                if (
                                    valid_polygon.is_valid
                                    and not valid_polygon.is_empty
                                ):
                                    polygons.append(
                                        (valid_polygon, int(severity_code), day)
                                    )
                            except Exception:
                                # Skip invalid polygons that cannot be made valid
                                continue
                    except Exception:
                        continue

        return polygons

    def point_in_polygon(self, *, point: Point, polygon: Polygon) -> bool:
        """Check if a point is within a polygon.

        Args:
            point: Point geometry (lon, lat).
            polygon: Polygon geometry.

        Returns:
            True if point is within polygon, False otherwise.
        """
        return bool(polygon.contains(point))
