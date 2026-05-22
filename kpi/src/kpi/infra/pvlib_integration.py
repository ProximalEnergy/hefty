import pandas as pd
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
