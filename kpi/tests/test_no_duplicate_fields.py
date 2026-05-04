"""Registry guards for duplicate field and upload keys."""

# ruff: noqa: I001
from kpi.registry.download.api import DownloadRegistry  # pyright: ignore[reportMissingImports]
from kpi.registry.transform.api import Transform  # pyright: ignore[reportMissingImports]
from kpi.registry.upload.api import UPLOAD  # pyright: ignore[reportMissingImports]


def test_no_duplicate_transform_download_fields() -> None:
    """Building Transform+Download map should not raise duplicate errors."""

    class DownloadTransform(Transform, DownloadRegistry):
        pass

    mapping = DownloadTransform.map()
    assert mapping


def test_no_duplicate_upload_keys() -> None:
    """Upload registry construction should not raise duplicate key errors."""
    assert UPLOAD
