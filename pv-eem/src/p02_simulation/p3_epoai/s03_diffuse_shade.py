from dataclasses import dataclass

import pandas as pd
from interfaces import Indeces, StringMetTimeSeries, SystemSeries
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation._utils.data_factorizer import factorize
from p02_simulation.p3_epoai.s01_direct_shade import ModelCircumsolar
from p02_simulation.p3_epoai.s02_electrical_effect import EPOAIfterElectricalEffect
from pvlib.shading import masking_angle, sky_diffuse_passias


@dataclass(init=False, slots=True)
class EPOAIafterDiffuseShade:
    """EPOAIafterDiffuseShade."""

    beam: StringMetTimeSeries
    circumsolar: StringMetTimeSeries
    horizon: StringMetTimeSeries
    isotropic: StringMetTimeSeries
    ground_diffuse: StringMetTimeSeries
    rear: StringMetTimeSeries

    def __init__(
        self,
        model_circumsolar: ModelCircumsolar,
        indeces: Indeces,
        epoai_after_electrical_effect: EPOAIfterElectricalEffect,
        racking_controls_gcr: SystemSeries,
        surface_tilt: StringMetTimeSeries,
    ):
        """Calculate the diffuse shading effect of the array"""
        # --- CONSTANTS ---
        SLANT_HEIGHT = 0.0

        # --- MERGE ---
        inputs = merge_by_dimension(
            data_series=[
                surface_tilt,
                racking_controls_gcr,
            ],
            indeces=indeces,
            merge_how=MergeHow.LEFT,
        )

        # --- FACTORIZE ---
        inputs = factorize(
            dataframe=inputs,
            columns=["surface_tilt", "racking_controls_gcr"],
            rounding_precision=3,
        )

        unique_by_group = inputs.groupby("_unique_id").first()

        # --- FUNCTION ---
        mask_angle = masking_angle(
            surface_tilt=unique_by_group["surface_tilt"],
            gcr=unique_by_group["racking_controls_gcr"],
            slant_height=SLANT_HEIGHT,
        )

        unique_by_group["diffuse_shade_fraction"] = sky_diffuse_passias(
            masking_angle=mask_angle
        )

        # --- MERGE ---
        outputs = pd.merge(
            left=inputs,
            right=unique_by_group[["diffuse_shade_fraction"]],
            on=["_unique_id"],
            how="left",
        )

        # --- Assignments ---
        # Pass through
        self.beam = epoai_after_electrical_effect.beam
        self.rear = epoai_after_electrical_effect.rear
        self.ground_diffuse = epoai_after_electrical_effect.ground_diffuse

        # Calculations
        loss = 1 - outputs["diffuse_shade_fraction"]
        self.isotropic = StringMetTimeSeries(
            epoai_after_electrical_effect.isotropic * loss
        )
        self.horizon = StringMetTimeSeries(epoai_after_electrical_effect.horizon * loss)

        match model_circumsolar:
            case ModelCircumsolar.SEPARATE:
                self.circumsolar = epoai_after_electrical_effect.circumsolar
            case ModelCircumsolar.DIFFUSE:
                self.circumsolar = StringMetTimeSeries(
                    epoai_after_electrical_effect.circumsolar * loss
                )
            case _:
                raise ValueError(f"""
                    model_circumsolar must be one of
                    {ModelCircumsolar.__members__}
                    """)
