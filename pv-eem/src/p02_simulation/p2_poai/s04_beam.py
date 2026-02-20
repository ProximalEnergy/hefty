from dataclasses import dataclass

import pandas as pd
import pvlib
from interfaces import Indeces, MetTimeSeries, StringMetTimeSeries, TimeSeries
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation._utils.data_factorizer import factorize


@dataclass(init=False, slots=True)
class Beam:
    """Beam."""

    beam: StringMetTimeSeries

    def __init__(
        self,
        indeces: Indeces,
        dni: MetTimeSeries,
        surface_tilt: StringMetTimeSeries,
        surface_azimuth: StringMetTimeSeries,
        apparent_zenith: TimeSeries,
        azimuth: TimeSeries,
    ):
        # --- MERGE ---
        inputs = merge_by_dimension(
            data_series=[
                dni,
                surface_tilt,
                surface_azimuth,
                apparent_zenith,
                azimuth,
            ],
            merge_how=MergeHow.LEFT,
            indeces=indeces,
        )

        # --- CALCULATE unique_id ---
        # This will assign incrementing numbers to unique combinations of
        # tracker algorithm inputs
        inputs = factorize(
            dataframe=inputs,
            columns=[
                "time",
                "dni",
                "surface_tilt",
                "surface_azimuth",
                "apparent_zenith",
                "azimuth",
            ],
        )

        # only pull out unique combinations
        unique_by_group = inputs.groupby("_unique_id").first()

        # --- FUNCTION ---
        beam_series = pvlib.irradiance.beam_component(
            surface_tilt=unique_by_group["surface_tilt"],
            surface_azimuth=unique_by_group["surface_azimuth"],
            solar_zenith=unique_by_group["apparent_zenith"],
            solar_azimuth=unique_by_group["azimuth"],
            dni=unique_by_group["dni"],
        )

        # Only positional indexes on dataframes allowed
        beam_series = beam_series.rename("beam")
        beam = beam_series.reset_index()

        # --- MERGE ---
        outputs = pd.merge(
            inputs,
            right=beam[["_unique_id", "beam"]],
            on=["_unique_id"],
            how="inner",
        )

        self.beam = StringMetTimeSeries(outputs.loc[:, "beam"])
