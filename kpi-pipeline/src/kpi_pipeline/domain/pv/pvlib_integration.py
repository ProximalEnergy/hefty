import numpy as np
import pandas as pd
import xarray as xr
from core import models
from pvlib import (  # type: ignore
    irradiance,
    location,
    tracking,
)
from shapely import wkb  # type: ignore

from kpi_pipeline.infra.data_access.pandas_to_xarray import (
    pandas_time_series_to_xarray,
)


def get_solar_position(
    site_location: location.Location,
    times: pd.DatetimeIndex,
) -> pd.DataFrame:
    return site_location.get_solarposition(times)  # type: ignore


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

    return tracking_df  # type: ignore


def get_location(project: models.Project) -> location.Location:
    """Extract location from project's WKBElement point geometry."""
    # Extract lat/long from WKBElement point
    geometry = wkb.loads(project.point.desc)  # type: ignore
    latitude = geometry.y
    longitude = geometry.x

    return location.Location(
        name=project.name_long,
        latitude=latitude,
        longitude=longitude,
        altitude=project.elevation or 0.0,
        tz=project.time_zone,
    )


def get_clear_sky(
    site_location: location.Location, times: pd.DatetimeIndex
) -> pd.DataFrame:
    clearsky = site_location.get_clearsky(times)
    return clearsky  # type: ignore


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

    return poa_irradiance  # type: ignore


def theoretical_poa_irradiance(
    project: models.Project,
    start_time_utc: np.datetime64,
    end_time_utc: np.datetime64,
) -> xr.DataArray:
    times = pd.date_range(
        start=start_time_utc, end=end_time_utc, freq="5min", inclusive="both"
    )
    site_location = get_location(project)
    solar_position = get_solar_position(site_location, times)
    tracking_df = get_tracker_angles(solar_position)
    clearsky = get_clear_sky(site_location, times)
    poa_irradiance = get_poa_irradiance(clearsky, solar_position, tracking_df)
    return pandas_time_series_to_xarray(poa_irradiance["poa_global"])
