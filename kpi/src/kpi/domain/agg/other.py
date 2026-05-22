import xarray as xr
from core.enumerations import DeviceTypeEnum

from kpi.base.util import coord
from kpi.domain.agg.resample import resample_sum


def daily_mean_across_devices(
    *,
    value: xr.DataArray,
    device_type: DeviceTypeEnum,
    date_local_5m: xr.DataArray,
) -> xr.DataArray:
    """Per-day mean of ``value`` across devices, counting only non-null samples.

    Args:
        value: DataArray with a dimension for ``device_type``.
        device_type: Device enum naming the dimension to average over.
        date_local_5m: Local date coordinate for daily resampling.

    Returns:
        Daily sum divided by daily count of reporting devices (non-null), with
        zero-safe denominator handling.
    """
    present_across_devices = value.notnull().sum(dim=coord(device_type))
    is_valid_sum = resample_sum(present_across_devices, grouper=date_local_5m)
    across_devices_sum = value.sum(dim=coord(device_type))
    value_sum = resample_sum(across_devices_sum, grouper=date_local_5m)
    return value_sum / is_valid_sum.where(is_valid_sum > 0)


def daily_mean_across_grouped_devices(
    *,
    value: xr.DataArray,
    device_mapping: xr.DataArray,
    device_type: DeviceTypeEnum,
    date_local_5m: xr.DataArray,
) -> xr.DataArray:
    """Daily mean after collapsing devices with ``device_mapping`` then summing.

    Args:
        value: Per-device series on the 5-minute grid.
        device_mapping: Maps each device coordinate to a parent/group label.
        device_type: Device enum for the dimension renamed before ``groupby``.
        date_local_5m: Local date for daily aggregation.

    Returns:
        Ratio of doubly grouped sums: totals over groups and days divided by
        counts of non-null contributions with zero-safe denominators.
    """
    is_valid_sum = (
        value.notnull()
        .groupby(device_mapping.rename(coord(device_type)))
        .sum()
        .groupby(date_local_5m)
        .sum()
    )
    value_sum = (
        value.groupby(device_mapping.rename(coord(device_type)))
        .sum()
        .groupby(date_local_5m)
        .sum()
    )
    return value_sum / is_valid_sum.where(is_valid_sum > 0)
