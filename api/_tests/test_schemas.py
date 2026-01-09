# test_schemas.py

import pytest
from app.interfaces import Point, convert
from geoalchemy2.shape import from_shape
from shapely.geometry import Point as ShapelyPoint


def test_point_valid_geojson_input():
    """Tests successful creation with valid GeoJSON format."""
    geojson_data = {"type": "Point", "coordinates": [10.5, -20.2]}
    point = Point.model_validate(geojson_data)
    assert isinstance(point, Point)
    assert point.type == "Point"
    assert point.coordinates == [10.5, -20.2]
    assert point.model_dump() == {"type": "Point", "coordinates": [10.5, -20.2]}


def test_point_valid_wkb_conversion():
    """Tests conversion from WKBElement to Point using the convert function."""
    # Create a Shapely Point and convert to WKBElement
    shapely_point = ShapelyPoint(10.5, -20.2)
    wkb_element = from_shape(shapely_point)

    # Convert WKBElement to GeoJSON format
    geojson_data = convert(WKBElement=wkb_element)

    # Validate with Point model
    point = Point.model_validate(geojson_data)
    assert isinstance(point, Point)
    assert point.type == "Point"
    assert point.coordinates == [10.5, -20.2]


def test_point_invalid_coordinates_length():
    """Tests validation error when coordinates have wrong length."""
    # Too few coordinates
    with pytest.raises(ValueError):
        Point.model_validate({"type": "Point", "coordinates": [10.5]})

    # Too many coordinates
    with pytest.raises(ValueError):
        Point.model_validate({"type": "Point", "coordinates": [10.5, -20.2, 100.0]})


def test_point_invalid_coordinate_types():
    """Tests validation error when coordinates are not floats."""
    with pytest.raises((ValueError, TypeError)):
        Point.model_validate(
            {"type": "Point", "coordinates": ["not_a_number", "also_not_a_number"]}
        )


def test_convert_none():
    """Test convert with None input."""
    result = convert(WKBElement=None)
    assert result is None


def test_convert_function_with_wkb_element():
    """Tests convert function properly converts WKBElement to GeoJSON."""
    # Create a Shapely Point and convert to WKBElement
    shapely_point = ShapelyPoint(10.5, -20.2)
    wkb_element = from_shape(shapely_point)

    # Convert to GeoJSON
    result = convert(WKBElement=wkb_element)

    assert result is not None
    assert result["type"] == "Point"
    assert list(result["coordinates"]) == [10.5, -20.2]
