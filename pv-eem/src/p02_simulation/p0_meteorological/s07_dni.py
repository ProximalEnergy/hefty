# --- Imports ---
from dataclasses import dataclass
from enum import StrEnum

import pandas as pd
import pvlib
from interfaces import Indeces, MetTimeSeries, TimeSeries
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension


# --- Enums ---
class ModelDecomposition(StrEnum):
    """ModelDecomposition."""

    DIRINT = "dirint"
    ERBS_DRIESSE = "erbs_driesse"


@dataclass(init=False, slots=True)
class DNI:
    """DNI."""

    dni: MetTimeSeries

    # --- Function ---
    def __init__(
        self,
        *,
        model: ModelDecomposition,
        indeces: Indeces,
        site_pressure: float,
        zenith: TimeSeries,
        temp_dew: MetTimeSeries,
        ghi: MetTimeSeries,
        dni_extra: TimeSeries,
    ):
        # --- Constants ---
        MIN_COS_ZENITH = 0.065  # default
        MAX_ZENITH = 87  # default

        inputs: pd.DataFrame = merge_by_dimension(
            data_series=[
                zenith,
                temp_dew,
                ghi,
                dni_extra,
            ],
            merge_how=MergeHow.LEFT,
            indeces=indeces,
        )

        # --- Calculate DNI ---
        match model:
            case ModelDecomposition.DIRINT:
                # dirint requires non-refraction corrected zenith
                dni = pvlib.irradiance.dirint(
                    ghi=inputs["ghi"],
                    solar_zenith=inputs["zenith"],
                    times=inputs.index,
                    pressure=site_pressure,
                    temp_dew=temp_dew,
                    use_delta_kt_prime=True,
                    min_cos_zenith=MIN_COS_ZENITH,
                    max_zenith=MAX_ZENITH,
                )
            case ModelDecomposition.ERBS_DRIESSE:
                # erbs_driesse requires non-refraction corrected zenith
                dni = pvlib.irradiance.erbs_driesse(
                    ghi=inputs["ghi"],
                    zenith=inputs["zenith"],
                    datetime_or_doy=inputs.index,
                    dni_extra=inputs["dni_extra"],
                    min_cos_zenith=MIN_COS_ZENITH,
                    max_zenith=MAX_ZENITH,
                )["dni"]
            case _:
                raise ValueError(
                    "Decomposition Algorithm must be dirint | erbs_driesse"
                )

        self.dni = MetTimeSeries(dni)
