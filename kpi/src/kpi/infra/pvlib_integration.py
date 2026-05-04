from typing import SupportsFloat

import pandas as pd
import xarray as xr
from kpi.domain.util import get_single_float_value
from kpi.infra.pandas_to_xarray import (
    pandas_time_series_to_xarray,
)
from pvlib import (  # type: ignore
    irradiance,
    location,
    tracking,
)


def get_solar_position(
    site_location: location.Location,
    times: pd.DatetimeIndex,
) -> pd.DataFrame:
    return site_location.get_solarposition(times)


def get_tracker_angles(
    solar_position: pd.DataFrame,
    axis_tilt: float = 0,
    axis_azimuth: float = 180,
    max_angle: float = 60,
    backtrack: bool = False,
    gcr: float = 0.5,
) -> pd.DataFrame:
    """
    originally from proximal-toolkit
    """
    tracking_df = tracking.singleaxis(
        apparent_zenith=solar_position["apparent_zenith"],
        solar_azimuth=solar_position["azimuth"],
        axis_tilt=axis_tilt,
        axis_azimuth=axis_azimuth,
        max_angle=max_angle,
        backtrack=backtrack,
        gcr=gcr,
    )
    tracking_df["tracker_theta"] = tracking_df["tracker_theta"].fillna(0)
    tracking_df["surface_azimuth"] = tracking_df["surface_azimuth"].fillna(0)

    return tracking_df


def get_clear_sky(
    site_location: location.Location, times: pd.DatetimeIndex
) -> pd.DataFrame:
    clearsky = site_location.get_clearsky(times)
    return clearsky


def get_poa_irradiance(
    clearsky: pd.DataFrame,
    solar_position: pd.DataFrame,
    tracking_df: pd.DataFrame,
) -> pd.DataFrame:
    poa_irradiance = irradiance.get_total_irradiance(
        surface_tilt=tracking_df["tracker_theta"].abs(),
        surface_azimuth=tracking_df["surface_azimuth"],
        dni=clearsky["dni"],
        ghi=clearsky["ghi"],
        dhi=clearsky["dhi"],
        solar_zenith=solar_position["apparent_zenith"],
        solar_azimuth=solar_position["azimuth"],
    )

    return poa_irradiance


def theoretical_poa_irradiance(
    time_utc: pd.DatetimeIndex,
    latitude: xr.DataArray | SupportsFloat,
    longitude: xr.DataArray | SupportsFloat,
    time_zone: str,
    altitude_m: xr.DataArray | None | SupportsFloat = 0,
) -> xr.DataArray:
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
