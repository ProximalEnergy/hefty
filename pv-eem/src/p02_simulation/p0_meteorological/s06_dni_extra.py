from dataclasses import dataclass
from enum import StrEnum

import pandas as pd
import pvlib
from interfaces import Indeces, TimeSeries


class ModelExtraTerrestrialDNI(StrEnum):
    """ModelExtraTerrestrialDNI."""

    SPENCER = "spencer"


@dataclass(init=False, slots=True)
class DNIExtra:
    """DNIExtra."""

    dni_extra: TimeSeries

    def __init__(
        self,
        *,
        model: ModelExtraTerrestrialDNI,
        indeces: Indeces,
    ):
        """Initialize the instance."""
        # --- CONSTANTS ---
        # Thish is the defaul value in pvlib, but it only applies to
        # the pyephem or nrel methods
        EPOCH_YEAR: int = 2014

        # solar_constant:
        #  * https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2010GL045777
        SOLAR_CONSTANT: float = 1360.8

        # --- CALCULATION ---
        # Get DatetimeIndex from time data
        time = pd.DatetimeIndex(indeces.time_index)

        # pvlib:  Typing doesn't work with generic return type from pvlib
        dni_extra_result = pd.Series(
            pvlib.irradiance.get_extra_radiation(
                datetime_or_doy=time,
                method=model,
                epoch_year=EPOCH_YEAR,
                solar_constant=SOLAR_CONSTANT,
            )
        )
        dni_extra_series = dni_extra_result.reset_index(drop=True)
        dni_extra_series.name = "dni_extra"
        self.dni_extra = TimeSeries(dni_extra_series)
