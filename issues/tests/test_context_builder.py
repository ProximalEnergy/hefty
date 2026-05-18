import polars as pl
from core.enumerations import SensorTypeEnum
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from issues.orchestrator.context_builder import _build_channels_from_tags


def test_build_channels_prefers_device_coordinates() -> None:
    """Device coordinates take precedence over project coordinates."""
    device_point = from_shape(Point(-96.5, 34.5), srid=4326)
    tags = pl.DataFrame(
        {
            "device_id": [10],
            "tag_id": [20],
            "device_point": [device_point],
        }
    )

    channels = _build_channels_from_tags(
        tags=tags,
        default_interval=5,
        project_latitude=35.1,
        project_longitude=-97.2,
    )

    assert len(channels) == 1
    assert channels[0].latitude == 34.5
    assert channels[0].longitude == -96.5


def test_build_channels_falls_back_to_project_coordinates() -> None:
    """Project coordinates are used when device coordinates are missing."""
    tags = pl.DataFrame(
        {
            "device_id": [10],
            "tag_id": [20],
            "device_point": [None],
        }
    )

    channels = _build_channels_from_tags(
        tags=tags,
        default_interval=5,
        project_latitude=35.1,
        project_longitude=-97.2,
    )

    assert len(channels) == 1
    assert channels[0].latitude == 35.1
    assert channels[0].longitude == -97.2


def test_build_channels_reads_geojson_device_point() -> None:
    """GeoJSON device points are converted into channel coordinates."""
    tags = pl.DataFrame(
        {
            "device_id": [10],
            "tag_id": [20],
            "device_point": [
                {
                    "type": "Point",
                    "coordinates": [-96.25, 34.25],
                }
            ],
        }
    )

    channels = _build_channels_from_tags(
        tags=tags,
        default_interval=5,
        project_latitude=35.1,
        project_longitude=-97.2,
    )

    assert len(channels) == 1
    assert channels[0].latitude == 34.25
    assert channels[0].longitude == -96.25


def test_build_channels_reads_memoryview_device_point() -> None:
    """Memoryview WKB device points are converted into channel coordinates."""
    raw_point = from_shape(Point(-96.75, 34.75), srid=4326).data
    tags = pl.DataFrame(
        {
            "device_id": [10],
            "tag_id": [20],
            "device_point": [memoryview(raw_point)],
        }
    )

    channels = _build_channels_from_tags(
        tags=tags,
        default_interval=5,
        project_latitude=35.1,
        project_longitude=-97.2,
    )

    assert len(channels) == 1
    assert channels[0].latitude == 34.75
    assert channels[0].longitude == -96.75


def test_build_channels_coerces_float_sensor_type_id() -> None:
    """Float sensor type IDs are preserved when building channels."""
    sensor_type_id = SensorTypeEnum.MET_STATION_POA_TILT.value
    tags = pl.DataFrame(
        {
            "device_id": [10],
            "tag_id": [20],
            "sensor_type_id": [float(sensor_type_id)],
            "device_point": [None],
        }
    )

    channels = _build_channels_from_tags(
        tags=tags,
        default_interval=5,
        project_latitude=35.1,
        project_longitude=-97.2,
    )

    assert len(channels) == 1
    assert channels[0].sensor_type_id == sensor_type_id


def test_build_channels_coerces_string_float_sensor_type_id() -> None:
    """String-float sensor type IDs are preserved when building channels."""
    sensor_type_id = SensorTypeEnum.MET_STATION_POA_TILT.value
    tags = pl.DataFrame(
        {
            "device_id": [10],
            "tag_id": [20],
            "sensor_type_id": [str(float(sensor_type_id))],
            "device_point": [None],
        }
    )

    channels = _build_channels_from_tags(
        tags=tags,
        default_interval=5,
        project_latitude=35.1,
        project_longitude=-97.2,
    )

    assert len(channels) == 1
    assert channels[0].sensor_type_id == sensor_type_id
