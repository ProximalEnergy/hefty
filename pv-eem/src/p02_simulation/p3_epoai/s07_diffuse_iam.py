import pandas as pd
import pvlib
from interfaces import Indeces, StringMetTimeSeries
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation.p3_epoai.s01_direct_shade import ModelCircumsolar
from p02_simulation.p3_epoai.s06_direct_iam import EPOAIafterDirectIAM


class EPOAIafterDiffuseIAM:
    """EPOAIafterDiffuseIAM."""

    beam: StringMetTimeSeries
    horizon: StringMetTimeSeries
    isotropic: StringMetTimeSeries
    circumsolar: StringMetTimeSeries
    ground_diffuse: StringMetTimeSeries
    rear: StringMetTimeSeries

    def __init__(
        self,
        model_circumsolar: ModelCircumsolar,
        indeces: Indeces,
        epoai_direct_iam: EPOAIafterDirectIAM,
        surface_tilt: StringMetTimeSeries,
    ):
        """Initialize the instance."""
        # --- CONSTANTS ---
        # Physical Model constants
        # TO DO:  Get the glass thickness from the module database
        K = 4.0  # glazing extinction coefficient [1/m]
        L = 0.0032  # glass thickness [m]
        REFRACTIVE_INDEX_GLASS = 1.526

        # --- MERGE ---
        inputs = merge_by_dimension(
            data_series=[
                surface_tilt,
                epoai_direct_iam._unique_id,
            ],
            indeces=indeces,
            merge_how=MergeHow.LEFT,
        )

        # --- GROUP ---
        # factorization already happened in the direct IAM step
        unique_by_group = inputs.groupby("_unique_id").first()

        # --- FUNCTION ---
        iam = pvlib.iam.marion_diffuse(
            model="physical",
            surface_tilt=unique_by_group["surface_tilt"],
            n=REFRACTIVE_INDEX_GLASS,
            K=K,
            L=L,
        )
        iam["isotropic"] = iam.pop("sky")
        iam["ground_diffuse"] = iam.pop("ground")
        suffix = "_factor"
        iam = {k + suffix: v for k, v in iam.items()}
        iam = pd.concat(iam.values(), axis=1, keys=iam.keys())

        # --- RECOMBINE ---
        outputs = pd.merge(
            left=inputs,
            right=iam,
            on="_unique_id",
            how="left",
        ).copy()

        # Pass throughs (components not affected by diffuse IAM)
        self.beam = epoai_direct_iam.beam
        self.rear = epoai_direct_iam.rear

        # Apply diffuse IAM to diffuse components
        self.horizon = StringMetTimeSeries(
            outputs["horizon_factor"] * epoai_direct_iam.horizon
        )
        self.isotropic = StringMetTimeSeries(
            outputs["isotropic_factor"] * epoai_direct_iam.isotropic
        )
        self.ground_diffuse = StringMetTimeSeries(
            outputs["ground_diffuse_factor"] * epoai_direct_iam.ground_diffuse
        )

        # Handle circumsolar component based on model
        match model_circumsolar:
            case ModelCircumsolar.SEPARATE:
                # Circumsolar is not affected by diffuse IAM when treated separately
                self.circumsolar = epoai_direct_iam.circumsolar
            case ModelCircumsolar.DIFFUSE:
                # Circumsolar is treated as diffuse and gets isotropic IAM factor
                self.circumsolar = StringMetTimeSeries(
                    outputs["isotropic_factor"] * epoai_direct_iam.circumsolar
                )
            case _:
                raise ValueError(f"""
                    model_circumsolar must be one of
                    {ModelCircumsolar.__members__}
                    """)
