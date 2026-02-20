from dataclasses import dataclass
from enum import StrEnum

import numpy as np
import pandas as pd
import pvlib
from interfaces import Indeces, ModuleEquipmentSeries, StringMetTimeSeries, SystemSeries
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation._utils.data_factorizer import factorize
from p02_simulation.p3_epoai.s01_direct_shade import ModelCircumsolar
from p02_simulation.p3_epoai.s05_soiling import EPOAIafterSoiling


class ModelIncidenceAngleModifier(StrEnum):
    """ModelIncidenceAngleModifier."""

    PHYSICAL = "Physical"
    TABULAR = "Tabular"


@dataclass(slots=True, init=False)
class EPOAIafterDirectIAM:
    """EPOAIafterDirectIAM."""

    beam: StringMetTimeSeries
    horizon: StringMetTimeSeries
    isotropic: StringMetTimeSeries
    circumsolar: StringMetTimeSeries
    ground_diffuse: StringMetTimeSeries
    rear: StringMetTimeSeries
    _unique_id: StringMetTimeSeries

    def __init__(
        self,
        model_iam: ModelIncidenceAngleModifier,
        model_circumsolar: ModelCircumsolar,
        indeces: Indeces,
        epoai_soiling: EPOAIafterSoiling,
        module_id_by_string: SystemSeries,
        module_has_ar_coating: ModuleEquipmentSeries,
        aoi: StringMetTimeSeries,
    ):
        """Initialize the instance."""
        # --- CONSTANTS ---
        # Physical Model constants
        # TO DO:  Get the glass thickness from the module database
        K = 4.0  # glazing extinction coefficient [1/m]
        L = 0.0032  # glass thickness [m]
        REFRACTIVE_INDEX_GLASS = 1.526
        REFRACTIVE_INDEX_AR_COATING = 1.29
        REFRACTIVE_INDEX_NO_COATING = 1.0

        # --- MERGE ---
        inputs = merge_by_dimension(
            data_series=[
                module_id_by_string,
                module_has_ar_coating,
                aoi,
            ],
            indeces=indeces,
            merge_how=MergeHow.LEFT,
        )

        # --- INTERMEDIATE CALCULATIONS ---
        # Calculate the refractive index of the anti-reflective (ar) coating
        # Which is 1.29 if it exists and 1.0 otherwise
        inputs["n_ar"] = np.where(
            inputs["has_ar_coating"],
            REFRACTIVE_INDEX_AR_COATING,
            REFRACTIVE_INDEX_NO_COATING,
        )

        # --- FACTORIZE ---
        inputs = factorize(
            dataframe=inputs,
            columns=["aoi", "n_ar"],
            rounding_precision=2,
        )

        unique_by_group = inputs.groupby("_unique_id").first()

        # --- FUNCTION ---
        match model_iam:
            case ModelIncidenceAngleModifier.PHYSICAL:
                iam: pd.Series = pvlib.iam.physical(
                    aoi=unique_by_group["aoi"],
                    n=REFRACTIVE_INDEX_GLASS,
                    K=K,
                    L=L,
                    n_ar=unique_by_group["n_ar"],
                )
            case ModelIncidenceAngleModifier.TABULAR:
                raise ValueError("Tabular model not implemented yet")
            case _:
                raise ValueError(f"Unknown model: {model_iam}.  Must be PHYSICAL")

        # Only allow dataframes with positional indices
        iam = iam.rename("iam")

        # --- REJOIN ---
        outputs = pd.merge(
            left=inputs,
            right=iam,
            on=["_unique_id"],
            how="left",
        )

        # Pass throughs
        self.rear = epoai_soiling.rear
        self.horizon = epoai_soiling.horizon
        self.isotropic = epoai_soiling.isotropic
        self.ground_diffuse = epoai_soiling.ground_diffuse

        # Calculated values
        self._unique_id = StringMetTimeSeries(outputs.loc[:, "_unique_id"])
        self.beam = StringMetTimeSeries(
            (epoai_soiling.beam * outputs.loc[:, "iam"]).rename("beam")
        )

        match model_circumsolar:
            case ModelCircumsolar.SEPARATE:
                self.circumsolar = StringMetTimeSeries(
                    (epoai_soiling.circumsolar * outputs.loc[:, "iam"]).rename(
                        "circumsolar"
                    )
                )
            case ModelCircumsolar.DIFFUSE:
                self.circumsolar = epoai_soiling.circumsolar
            case _:
                raise ValueError(f"""
                    model_circumsolar must be one of
                    {ModelCircumsolar.__members__}
                    """)
