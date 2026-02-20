from dataclasses import dataclass

import pandas as pd
import pvlib
from interfaces import Indeces, MetTimeSeries, StringMetTimeSeries
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation._utils.data_factorizer import factorize


@dataclass(init=False, slots=True)
class GroundDiffuse:
    """GroundDiffuse."""

    ground_diffuse: StringMetTimeSeries

    def __init__(
        self,
        indeces: Indeces,
        ghi: MetTimeSeries,
        surface_tilt: StringMetTimeSeries,
        ALBEDO: float,
    ):
        """Calculate the ground diffuse irradiance (POAI)"""
        inputs = merge_by_dimension(
            data_series=[
                ghi,
                surface_tilt,
            ],
            merge_how=MergeHow.LEFT,
            indeces=indeces,
        )

        # --- FACTORIZE ---
        # This will assign incrementing numbers to unique combinations of
        # ground_diffuse_inputs
        inputs = factorize(
            dataframe=inputs,
            columns=["time", "ghi", "surface_tilt"],
        )

        # only pull out unique combinations
        unique_by_group = inputs.groupby("_unique_id").first()

        # --- FUNCTION ---
        ground_diffuse_series = pvlib.irradiance.get_ground_diffuse(
            surface_tilt=unique_by_group["surface_tilt"],
            ghi=unique_by_group["ghi"],
            albedo=ALBEDO,
            surface_type=None,  # use albedo instead
        )

        # Only positional indexes on dataframes allowed
        ground_diffuse_series = ground_diffuse_series.rename("ground_diffuse")
        ground_diffuse = ground_diffuse_series.reset_index()

        # --- MERGE ---
        outputs = pd.merge(
            inputs,
            right=ground_diffuse[["_unique_id", "ground_diffuse"]],
            on=["_unique_id"],
            how="inner",
        )

        self.ground_diffuse = StringMetTimeSeries(outputs.loc[:, "ground_diffuse"])
