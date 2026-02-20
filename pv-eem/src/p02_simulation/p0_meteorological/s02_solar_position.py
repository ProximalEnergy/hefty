# --- Imports ---
# Typing
from dataclasses import dataclass
from enum import StrEnum

import pandas as pd

# Main Imports
import pvlib
from interfaces import Indeces, MetTimeSeries, TimeSeries


class ModelSolarPositionAlgorithm(StrEnum):
    """ModelSolarPositionAlgorithm."""

    NREL2008 = "NREL_2008"


@dataclass(init=False, slots=True)
class SolarPosition:
    """SolarPosition."""

    apparent_zenith: TimeSeries
    zenith: TimeSeries
    apparent_elevation: TimeSeries
    elevation: TimeSeries
    azimuth: TimeSeries
    equation_of_time: TimeSeries

    # --- Function ---
    def __init__(
        self,
        model: ModelSolarPositionAlgorithm,
        latitude: float,
        longitude: float,
        elevation: float,
        indeces: Indeces,
        ambient_temperature: MetTimeSeries,
        sun_position_offset: float,
    ):
        # --- INPUTS ---
        inputs = pd.DataFrame(
            {
                "time": indeces.met_time_index.loc[:, "time"]
                + pd.Timedelta(minutes=sun_position_offset),
                "met_name": indeces.met_time_index.loc[:, "met_name"],
                "ambient_temperature": ambient_temperature,
            }
        )

        # --- FACTORIZE ---
        unique_by_group = inputs.groupby("time").first()
        time = pd.DatetimeIndex(unique_by_group.index)
        temperature = unique_by_group["ambient_temperature"]

        # --- FUNCTION ---
        match model:
            case ModelSolarPositionAlgorithm.NREL2008:
                solar_position: pd.DataFrame = pvlib.solarposition.get_solarposition(
                    time=time,
                    latitude=latitude,
                    longitude=longitude,
                    altitude=elevation,
                    pressure=None,
                    temperature=temperature,
                )
            case _:
                raise ValueError("Solar Position Algorithm must be NREL2008")

        solar_position = solar_position.reset_index()
        self.apparent_zenith = TimeSeries(solar_position.loc[:, "apparent_zenith"])
        self.zenith = TimeSeries(solar_position.loc[:, "zenith"])
        self.apparent_elevation = TimeSeries(
            solar_position.loc[:, "apparent_elevation"]
        )
        self.elevation = TimeSeries(solar_position.loc[:, "elevation"])
        self.azimuth = TimeSeries(solar_position.loc[:, "azimuth"])
        self.equation_of_time = TimeSeries(solar_position.loc[:, "equation_of_time"])
