from dataclasses import dataclass
from enum import StrEnum

import pandas as pd
import pvlib
from interfaces import MetTimeSeries


class ModelTDew(StrEnum):
    """ModelTDew."""

    MAGNUS_TETENS = "magnus_tetens"


@dataclass(init=False, slots=True)
class TemperatureDewPoint:
    """TemperatureDewPoint."""

    temperature_dew_point: MetTimeSeries

    def __init__(
        self,
        *,
        model: ModelTDew,
        ambient_temperature: MetTimeSeries,
        relative_humidity: MetTimeSeries,
    ):
        """Calculate the dew point temperature"""
        # --- CONSTANTS ---
        COEFFS = (6.112, 17.62, 243.12)  # defaults from pvlib

        # --- CALCULATE dewpoint temperature ---
        match model:
            case ModelTDew.MAGNUS_TETENS:
                dewpoint_temperature = pd.Series(
                    pvlib.atmosphere.tdew_from_rh(
                        temp_air=ambient_temperature,
                        relative_humidity=relative_humidity,
                        coeff=COEFFS,
                    )
                )
            case _:
                raise ValueError(f"Unknown model: {model}.  Must be MAGNUS_TETENS")

        dewpoint_temperature.reset_index(drop=True)
        dewpoint_temperature.name = "tdew"
        self.temperature_dew_point = MetTimeSeries(dewpoint_temperature)
