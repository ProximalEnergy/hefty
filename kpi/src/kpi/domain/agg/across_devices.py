import xarray as xr
from core.enumerations import DeviceTypeEnum

from kpi.base.util import coord


def mean_across_devices(
    x: xr.DataArray,
    *,
    device_type: DeviceTypeEnum,
) -> xr.DataArray:
    """Arithmetic mean over the device dimension named by ``device_type``.

    Args:
        x: Input with a device coordinate from ``coord(device_type)``.
        device_type: Which device axis to reduce.

    Returns:
        ``x.mean(dim=coord(device_type))``.
    """
    return x.mean(dim=coord(device_type))


def sum_across_devices(
    x: xr.DataArray,
    *,
    device_type: DeviceTypeEnum,
    min_count: int = 1,
) -> xr.DataArray:
    """Sum over the device dimension with optional ``min_count``.

    Args:
        x: Input with a device coordinate from ``coord(device_type)``.
        device_type: Which device axis to reduce.
        min_count: Minimum valid elements required for a non-NaN sum.

    Returns:
        ``x.sum(dim=..., min_count=min_count)``.
    """
    return x.sum(dim=coord(device_type), min_count=min_count)


def min_across_devices(
    x: xr.DataArray,
    *,
    device_type: DeviceTypeEnum,
) -> xr.DataArray:
    """Minimum over the device dimension.

    Args:
        x: Input with a device coordinate from ``coord(device_type)``.
        device_type: Which device axis to reduce.

    Returns:
        ``x.min(dim=coord(device_type))``.
    """
    return x.min(dim=coord(device_type))


def max_across_devices(
    x: xr.DataArray,
    *,
    device_type: DeviceTypeEnum,
) -> xr.DataArray:
    """Maximum over the device dimension.

    Args:
        x: Input with a device coordinate from ``coord(device_type)``.
        device_type: Which device axis to reduce.

    Returns:
        ``x.max(dim=coord(device_type))``.
    """
    return x.max(dim=coord(device_type))
