from dataclasses import dataclass
from enum import StrEnum

import pandas as pd
import pvlib
from interfaces import TimeSeries
from p02_simulation.p0_meteorological.s02_solar_position import SolarPosition


class ModelAirMassRelative(StrEnum):
    """ModelAirMassRelative."""

    KASTEN_YOUNG_1989 = "kastenyoung1989"


class ModelAirMassAbsolute(StrEnum):
    """ModelAirMassAbsolute."""

    GUEYMARD_1993 = "gueymard1993"


@dataclass(init=False, slots=True)
class AirMass:
    """AirMass."""

    relative: TimeSeries
    absolute: TimeSeries

    def __init__(
        self,
        model_airmass_relative: ModelAirMassRelative,
        model_airmass_absolute: ModelAirMassAbsolute,
        solar_position: SolarPosition,
        site_pressure: float,
    ):
        """Initialize the instance."""
        # --- Calculate Relative Air Mass ---
        match model_airmass_relative:
            case ModelAirMassRelative.KASTEN_YOUNG_1989:
                # KastenYoung1989 requires apparent zenith
                air_mass_relative = pd.Series(
                    pvlib.atmosphere.get_relative_airmass(
                        zenith=solar_position.apparent_zenith,
                        model=ModelAirMassRelative.KASTEN_YOUNG_1989,
                    )
                )
            case _:
                raise ValueError("ModelAirMassRelative must be KastenYoung1989")

        # --- Calculate Absolute Air Mass ---
        match model_airmass_absolute:
            case ModelAirMassAbsolute.GUEYMARD_1993:
                air_mass_absolute = pd.Series(
                    pvlib.atmosphere.get_absolute_airmass(
                        airmass_relative=air_mass_relative,
                        pressure=site_pressure,
                    )
                )
            case _:
                raise ValueError("ModelAirMassAbsolute must be Gueymard1993")

        air_mass_relative = air_mass_relative.reset_index(drop=True)
        air_mass_absolute = air_mass_absolute.reset_index(drop=True)
        air_mass_relative.name = "air_mass_relative"
        air_mass_absolute.name = "air_mass_absolute"
        self.relative = TimeSeries(air_mass_relative)
        self.absolute = TimeSeries(air_mass_absolute)
