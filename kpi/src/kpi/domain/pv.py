from typing import SupportsFloat

import pandas as pd
import xarray as xr
from pvlib import location  # type: ignore

from kpi.domain.util import filter_mask, get_single_float_value
from kpi.infra.pandas_to_xarray import pandas_time_series_to_xarray
from kpi.infra.pvlib_integration import (
    get_clear_sky,
    get_poa_irradiance,
    get_solar_position,
    get_tracker_angles,
)


def pv_filter_daily_energy(
    *,
    energy_unfiltered_d: xr.DataArray,
    power_capacity: xr.DataArray,
    max_specific_yield: float = 24,
) -> xr.DataArray:
    """Reject daily energy totals outside plausible specific-yield bounds.

    Keeps days where ``energy / power_capacity`` is in
    ``[-epsilon, max_specific_yield]``.

    Args:
        energy_unfiltered_d: Daily energy total (e.g. kWh).
        power_capacity: Nameplate or reference power (same energy-rate units).
        max_specific_yield: Upper bound on daily energy per unit capacity
            (full-sun-hours equivalent).

    Returns:
        ``energy_unfiltered_d`` with invalid ratios masked to NaN.
    """
    epsilon = 1e-6
    return energy_unfiltered_d.where(
        filter_mask(
            filter_by=energy_unfiltered_d / power_capacity,
            min_value=-epsilon,
            max_value=max_specific_yield,
        )
    )


def theoretical_poa_irradiance(
    time_utc: pd.DatetimeIndex,
    latitude: xr.DataArray | SupportsFloat,
    longitude: xr.DataArray | SupportsFloat,
    time_zone: str,
    altitude_m: xr.DataArray | None | SupportsFloat = 0,
) -> xr.DataArray:
    """Clear-sky plane-of-array irradiance for a single-axis tracked site.

    Uses pvlib to model solar position, default single-axis tracker geometry
    (north-south axis, 60° max tilt, no backtracking), Ineichen clear-sky
    irradiance, and POA ``poa_global`` on the tracked surface.

    Args:
        time_utc: UTC timestamps for the output series.
        latitude: Site latitude in degrees (scalar ``DataArray`` or float).
        longitude: Site longitude in degrees (scalar ``DataArray`` or float).
        time_zone: IANA timezone for the site (e.g. ``America/Chicago``).
        altitude_m: Site elevation above sea level in meters; defaults to 0.

    Returns:
        Global POA irradiance (W/m²) as an ``xr.DataArray`` indexed by
        ``time_utc``.
    """
    latitude = get_single_float_value(latitude)
    longitude = get_single_float_value(longitude)
    if altitude_m is None:
        altitude_m = 0.0
    else:
        altitude_m = get_single_float_value(altitude_m)
    site_location = location.Location(
        latitude=latitude,
        longitude=longitude,
        altitude=altitude_m,
        tz=time_zone,
    )
    solar_position = get_solar_position(site_location, time_utc)
    tracking_df = get_tracker_angles(solar_position)
    clearsky = get_clear_sky(site_location, time_utc)
    poa_irradiance = get_poa_irradiance(clearsky, solar_position, tracking_df)
    return pandas_time_series_to_xarray(poa_irradiance["poa_global"])
