from dataclasses import dataclass
from enum import StrEnum

import pandas as pd
import pvlib
from interfaces import (
    Indeces,
    MetTimeSeries,
    StringMetTimeSeries,
    TimeSeries,
)
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation._utils.data_factorizer import factorize


class ModelTransposition(StrEnum):
    """ModelTransposition."""

    PEREZ_DRIESSE = "Perez_Driesse"


@dataclass(init=False, slots=True)
class SkyDiffuse:
    """SkyDiffuse."""

    isotropic: StringMetTimeSeries
    circumsolar: StringMetTimeSeries
    horizon: StringMetTimeSeries

    def __init__(
        self,
        model: ModelTransposition,
        indeces: Indeces,
        surface_tilt: StringMetTimeSeries,
        surface_azimuth: StringMetTimeSeries,
        apparent_zenith: TimeSeries,
        azimuth: TimeSeries,
        dni: MetTimeSeries,
        dhi: MetTimeSeries,
        dni_extra: TimeSeries,
        air_mass_relative: TimeSeries,
    ):
        """Calculate the plane of array irradiance (sky_diffuse)
        via transposition model
        """
        # --- MERGE ---
        inputs = merge_by_dimension(
            data_series=[
                surface_tilt,
                surface_azimuth,
                apparent_zenith,
                azimuth,
                dni,
                dhi,
                dni_extra,
                air_mass_relative,
            ],
            merge_how=MergeHow.LEFT,
            indeces=indeces,
        )

        # --- CALCULATE sky_diffuse GROUP ID ---
        # This will assign incrementing numbers to unique combinations of
        # tracker algorithm inputs
        inputs = factorize(
            dataframe=inputs,
            columns=["time", "met_name", "surface_tilt", "surface_azimuth"],
        )

        # only pull out unique combinations
        unique_by_group = inputs.groupby("_unique_id").first()

        sky_diffuse = pd.DataFrame({})
        match model:
            case ModelTransposition.PEREZ_DRIESSE:
                # perez_driesse requires relative air mass
                sky_diffuse = pvlib.irradiance.perez_driesse(
                    surface_tilt=unique_by_group["surface_tilt"],
                    surface_azimuth=unique_by_group["surface_azimuth"],
                    dhi=unique_by_group["dhi"],
                    dni=unique_by_group["dni"],
                    dni_extra=unique_by_group["dni_extra"],
                    solar_zenith=unique_by_group["apparent_zenith"],
                    solar_azimuth=unique_by_group["azimuth"],
                    airmass=unique_by_group["air_mass_relative"],
                    return_components=True,
                )

            case _:
                sky_diffuse = pd.DataFrame({})
                raise ValueError(f"Unknown model: {model}.  Must be PEREZ")

        # Only positional indices allowed
        sky_diffuse = sky_diffuse.reset_index()

        # --- MERGE ---
        outputs = pd.merge(
            inputs,
            right=sky_diffuse[["_unique_id", "isotropic", "circumsolar", "horizon"]],
            on=["_unique_id"],
            how="left",
        )

        self.isotropic = StringMetTimeSeries(outputs.loc[:, "isotropic"])
        self.circumsolar = StringMetTimeSeries(outputs.loc[:, "circumsolar"])
        self.horizon = StringMetTimeSeries(outputs.loc[:, "horizon"])
