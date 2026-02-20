import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated

import pandas as pd
from interfaces import Indeces, MetTimeSeries, TimeSeries
from p01_get_data.class_simulation_inputs import MetDataObserved
from p02_simulation.p0_meteorological.s01_pressure import calc_site_pressure
from p02_simulation.p0_meteorological.s02_solar_position import SolarPosition
from p02_simulation.p0_meteorological.s03_air_mass import AirMass
from p02_simulation.p0_meteorological.s04_tdew import TemperatureDewPoint
from p02_simulation.p0_meteorological.s05_pwat import PrecipitableWater
from p02_simulation.p0_meteorological.s06_dni_extra import DNIExtra
from p02_simulation.p0_meteorological.s07_dni import DNI
from p02_simulation.p0_meteorological.s08_dhi import DHI

if TYPE_CHECKING:
    from p01_get_data.s00_get_simulation_config import SimulationConfig


@dataclass(init=False, slots=True)
class MetDataComputed:
    # Single Value Attributes
    """MetDataComputed."""

    site_pressure: Annotated[float, "Pa"]

    # Indexed by Timeseries Only
    solar_azimuth: Annotated[TimeSeries, "degrees"]
    solar_elevation: Annotated[TimeSeries, "degrees"]
    solar_zenith: Annotated[TimeSeries, "degrees"]
    solar_apparent_zenith: Annotated[TimeSeries, "degrees"]
    air_mass_relative: Annotated[TimeSeries, "dimensionless"]
    air_mass_absolute: Annotated[TimeSeries, "dimensionless"]
    dni_extra: Annotated[TimeSeries, "W/m²"]

    # Indexed by Timeseries and Met Station
    temp_dew: Annotated[MetTimeSeries, "°C"]
    precipitable_water: Annotated[MetTimeSeries, "cm"]
    dni: Annotated[MetTimeSeries, "W/m²"]
    dhi: Annotated[MetTimeSeries, "W/m²"]

    def __init__(
        self,
        *,
        latitude: float,
        longitude: float,
        elevation: float,
        indeces: Indeces,
        met_data_observed: MetDataObserved,
        simulation_config: "SimulationConfig",
    ):
        # --- HARDCODED ---
        # met station parameters
        _WIND_SENSOR_ELEVATION = 3.0  # m

        # --- Single Values ---
        site_pressure: float = calc_site_pressure(elevation=elevation)

        # --- Indexed by Time Only ---
        # LEGACY:  Right now all of these functions that are only indexed by time are
        # using the time_instrumental attribute which indexes by both time and
        # met_station.  We should refactor to not use the extra data
        solar_position = SolarPosition(
            model=simulation_config.spa,
            indeces=indeces,
            latitude=latitude,
            longitude=longitude,
            elevation=elevation,
            ambient_temperature=met_data_observed.ambient_temperature,
            sun_position_offset=simulation_config.sun_position_offset,
        )

        air_mass = AirMass(
            model_airmass_relative=simulation_config.airmass_relative,
            model_airmass_absolute=simulation_config.airmass_absolute,
            solar_position=solar_position,
            site_pressure=site_pressure,
        )

        dni_extra = DNIExtra(
            model=simulation_config.extra_terrestrial_dni,
            indeces=indeces,
        )

        # --- Indexed by Met Station and Time ---
        temp_dew = TemperatureDewPoint(
            model=simulation_config.dewpoint_temperature,
            ambient_temperature=met_data_observed.ambient_temperature,
            relative_humidity=met_data_observed.relative_humidity,
        )

        precipitable_water = PrecipitableWater(
            ambient_temperature=met_data_observed.ambient_temperature,
            relative_humidity=met_data_observed.relative_humidity,
        )

        dni = DNI(
            model=simulation_config.decomposition,
            indeces=indeces,
            site_pressure=site_pressure,
            temp_dew=temp_dew.temperature_dew_point,
            zenith=solar_position.zenith,
            ghi=met_data_observed.ghi,
            dni_extra=dni_extra.dni_extra,
        )

        dhi = DHI(
            indeces=indeces,
            ghi=met_data_observed.ghi,
            dni=dni.dni,
            zenith=solar_position.zenith,
        )

        #
        # --- Single Value Attributes ---
        #
        self.site_pressure = site_pressure
        #
        # --- Indexed by Timeseries Only ---
        #
        self.solar_azimuth = solar_position.azimuth
        self.solar_elevation = solar_position.elevation
        self.solar_zenith = solar_position.zenith
        self.solar_apparent_zenith = solar_position.apparent_zenith
        self.air_mass_relative = air_mass.relative
        self.air_mass_absolute = air_mass.absolute
        self.dni_extra = dni_extra.dni_extra
        #
        # --- Indexed by Timeseries and Met Station ---
        #
        self.temp_dew = temp_dew.temperature_dew_point
        self.precipitable_water = precipitable_water.precipitable_water
        self.dni = dni.dni
        self.dhi = dhi.dhi

    def to_timeseries_df(self, indeces):
        """Run to_timeseries_df."""
        return pd.DataFrame(
            {
                "time": indeces.time_index,
                "solar_azimuth": self.solar_azimuth,
                "solar_elevation": self.solar_elevation,
                "solar_zenith": self.solar_zenith,
                "solar_apparent_zenith": self.solar_apparent_zenith,
                "air_mass_relative": self.air_mass_relative,
                "air_mass_absolute": self.air_mass_absolute,
                "dni_extra": self.dni_extra,
            }
        )

    def to_timeseries_csv(self, indeces):
        """Run to_timeseries_csv."""
        df = self.to_timeseries_df(indeces)
        df.to_csv("met_data_computed.csv")
        logging.info(
            "Meteorological data computed and saved to 'met_data_computed.csv'"
        )
