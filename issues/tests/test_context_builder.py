import polars as pl
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from issues.orchestrator.context_builder import _build_channels_from_tags


def test_build_channels_prefers_device_coordinates() -> None:
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
