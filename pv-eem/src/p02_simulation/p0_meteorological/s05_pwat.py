from dataclasses import dataclass

import pandas as pd
import pvlib
from interfaces import MetTimeSeries


@dataclass(init=False, slots=True)
class PrecipitableWater:
    """PrecipitableWater."""

    precipitable_water: MetTimeSeries

    def __init__(
        self,
        *,
        ambient_temperature: pd.Series,
        relative_humidity: pd.Series,
    ):
        """Calculate precipitable water (cm) from local meteorological data.

        Parameters
        ----------
        time_instrumental : pd.Series
            Time series data
        met_name : pd.Series
            Met station names
        ambient_temperature : pd.Series
            Ambient temperature in °C
        relative_humidity : pd.Series
            Relative humidity in % out of 100

        Returns:
        -------
        pandas.DataFrame
            Precipitable water (mm) from local meteorological data.
        """
        # calculate precipitable water (mm)
        precipitable_water = pvlib.atmosphere.gueymard94_pw(
            temp_air=ambient_temperature,
            relative_humidity=relative_humidity,
        )

        self.precipitable_water = MetTimeSeries(
            precipitable_water.rename("precipitable_water")
        )
