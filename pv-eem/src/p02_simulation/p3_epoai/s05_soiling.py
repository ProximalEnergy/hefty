from dataclasses import dataclass
from enum import StrEnum

import numpy as np
import pandas as pd
from interfaces import Indeces, MetTimeSeries, StringMetTimeSeries
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation.p3_epoai.s04_rear_shade import EPOAIafterRearShade


class ModelSoiling(StrEnum):
    """ModelSoiling."""

    MEASURED = "measured"
    NONE = "none"


@dataclass(init=False, slots=True)
class EPOAIafterSoiling:
    """EPOAIafterSoiling."""

    beam: StringMetTimeSeries
    horizon: StringMetTimeSeries
    isotropic: StringMetTimeSeries
    circumsolar: StringMetTimeSeries
    ground_diffuse: StringMetTimeSeries
    rear: StringMetTimeSeries

    def __init__(
        self,
        model: ModelSoiling,
        indeces: Indeces,
        epoai_rear_shade: EPOAIafterRearShade,
        soil_percent: MetTimeSeries,
    ):
        """Calculate the effective plane of array irradiance (EPOAI)"""
        # --- Pre-calc ---
        # This is just done to use the StringMetTimeSeries
        # in the merge
        empty_series = StringMetTimeSeries(
            pd.Series(
                data=np.zeros(len(epoai_rear_shade.isotropic)),
                name="empty",
            )
        )

        # --- MERGE ---
        inputs = merge_by_dimension(
            data_series=[
                empty_series,
                soil_percent,
            ],
            indeces=indeces,
            merge_how=MergeHow.LEFT,
        )

        # --- FUNCTION ---
        match model:
            case ModelSoiling.NONE:
                inputs["soil_percent"] = 1.0
            case ModelSoiling.MEASURED:
                pass
            case _:
                raise ValueError("ModelSoiling must be MEASURED | NONE")

        # --- APPLY ---
        # Remove soiling from all plane of array components
        self.beam = StringMetTimeSeries(epoai_rear_shade.beam * inputs["soil_percent"])
        self.horizon = StringMetTimeSeries(
            epoai_rear_shade.horizon * inputs["soil_percent"]
        )
        self.isotropic = StringMetTimeSeries(
            epoai_rear_shade.isotropic * inputs["soil_percent"]
        )
        self.circumsolar = StringMetTimeSeries(
            epoai_rear_shade.circumsolar * inputs["soil_percent"]
        )
        self.ground_diffuse = StringMetTimeSeries(
            epoai_rear_shade.ground_diffuse * inputs["soil_percent"]
        )
        self.rear = StringMetTimeSeries(epoai_rear_shade.rear * inputs["soil_percent"])
