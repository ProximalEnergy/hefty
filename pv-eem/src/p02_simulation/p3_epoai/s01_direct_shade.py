from dataclasses import dataclass
from enum import StrEnum

import pandas as pd
import pvlib
from interfaces import (
    Indeces,
    ModuleEquipmentSeries,
    StringMetTimeSeries,
    SystemSeries,
    TimeSeries,
)
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation._utils.data_factorizer import factorize
from p02_simulation.p2_poai.c_poai import PlaneOfArrayIrradiance


class ModelCircumsolar(StrEnum):
    """ModelCircumsolar."""

    SEPARATE = "Separate"
    DIFFUSE = "Diffuse"


@dataclass(init=False, slots=True)
class EPOAIafterFrontShade:
    """EPOAIafterFrontShade."""

    beam: StringMetTimeSeries
    circumsolar: StringMetTimeSeries
    horizon: StringMetTimeSeries
    isotropic: StringMetTimeSeries
    ground_diffuse: StringMetTimeSeries
    rear: StringMetTimeSeries
    direct_shade_fraction: StringMetTimeSeries

    def __init__(
        self,
        model_circumsolar: ModelCircumsolar,
        indeces: Indeces,
        poai: PlaneOfArrayIrradiance,
        axis_azimuth: float,
        pitch: SystemSeries,
        apparent_zenith: TimeSeries,
        azimuth: TimeSeries,
        tracker_theta: StringMetTimeSeries,
        module_id_by_string: SystemSeries,
        module_length: ModuleEquipmentSeries,
    ):
        """Calculate the direct shading effect of the array"""
        # TO DO:  Discount for active cell area instead of module area
        #         aka frame.

        # --- HARDCODED ---
        AXIS_TILT = 0.0
        SURFACE_TO_AXIS_OFFSET = 0.0
        CROSS_AXIS_SLOPE = 0.0
        RACKING_NUM_MODULES_IN_PORTRAIT = 1

        # --- MERGE ---
        inputs = merge_by_dimension(
            indeces=indeces,
            data_series=[
                apparent_zenith,
                azimuth,
                pitch,
                tracker_theta,
                module_id_by_string,
                module_length,
            ],
            merge_how=MergeHow.LEFT,
        )

        # --- Intermediates ---
        inputs["collector_band_width"] = (
            inputs["length"] * RACKING_NUM_MODULES_IN_PORTRAIT
        )

        # --- FACTORIZE ---
        inputs = factorize(
            dataframe=inputs,
            columns=[
                "apparent_zenith",
                "azimuth",
                "pitch",
                "tracker_theta",
                "collector_band_width",
            ],
            rounding_precision=2,
        )

        unique_by_group = inputs.groupby("_unique_id").first()

        # --- FUNCTION ---
        direct_shade_fractions = pvlib.shading.shaded_fraction1d(
            solar_zenith=unique_by_group["apparent_zenith"],
            solar_azimuth=unique_by_group["azimuth"],
            axis_azimuth=axis_azimuth,
            shaded_row_rotation=unique_by_group["tracker_theta"],
            collector_width=unique_by_group["collector_band_width"],
            pitch=unique_by_group["pitch"],
            axis_tilt=AXIS_TILT,
            surface_to_axis_offset=SURFACE_TO_AXIS_OFFSET,
            cross_axis_slope=CROSS_AXIS_SLOPE,
            shading_row_rotation=None,  # shaded row angles == reference row angles
        )

        direct_shade_fractions = direct_shade_fractions.rename("direct_shade_fraction")

        # --- MERGE ---
        outputs = pd.merge(
            left=inputs,
            right=direct_shade_fractions,
            on=["_unique_id"],
            how="left",
        )

        # --- FUNCTION ---
        # Pass throughs
        self.rear = poai.rear
        self.horizon = poai.horizon
        self.isotropic = poai.isotropic

        # Calculated values
        # PlantPredict uses direct shade fraction on ground diffuse
        shade_loss = 1 - outputs.loc[:, "direct_shade_fraction"]
        self.beam = StringMetTimeSeries((poai.beam * shade_loss).rename("beam"))
        self.ground_diffuse = StringMetTimeSeries(
            (poai.ground_diffuse * shade_loss).rename("ground_diffuse")
        )

        match model_circumsolar:
            case ModelCircumsolar.SEPARATE:
                self.circumsolar = StringMetTimeSeries(
                    (poai.circumsolar * shade_loss).rename("circumsolar")
                )
            case ModelCircumsolar.DIFFUSE:
                self.circumsolar = poai.circumsolar
            case _:
                raise ValueError(f"""
                    model_circumsolar must be one of
                    {ModelCircumsolar.__members__}
                    """)

        self.direct_shade_fraction = StringMetTimeSeries(
            outputs.loc[:, "direct_shade_fraction"]
        )
