from dataclasses import dataclass

import pandas as pd
import pvlib
from interfaces import Indeces, StringMetTimeSeries
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation.p4_dc_iv.s02_single_diode_params import (
    SingleDiodeParameters,
)


@dataclass(init=False, slots=True)
class SingleDiodeModel:
    """SingleDiodeModel."""

    p_mp: StringMetTimeSeries
    i_mp: StringMetTimeSeries
    v_mp: StringMetTimeSeries
    i_sc: StringMetTimeSeries
    v_oc: StringMetTimeSeries

    def __init__(
        self,
        indeces: Indeces,
        single_diode_parameters: SingleDiodeParameters,
    ):
        # --- MERGE ---
        inputs = merge_by_dimension(
            data_series=[
                single_diode_parameters.photocurrent,
                single_diode_parameters.saturation_current,
                single_diode_parameters.resistance_series,
                single_diode_parameters.resistance_shunt,
                single_diode_parameters.nNsVth,
                single_diode_parameters._unique_ids,
            ],
            indeces=indeces,
            merge_how=MergeHow.LEFT,
        )

        # --- FACTORIZE ---
        # Can factorize by the same unique id's as the calculation of
        # the inputs parameters
        unique_by_group = inputs.groupby("_unique_id").first()
        unique_by_group = unique_by_group.reset_index()

        # --- FUNCTION ---
        # calculate iv curve at environmental conditions
        iv_curve_raw = pvlib.pvsystem.singlediode(
            photocurrent=unique_by_group["photocurrent"],
            saturation_current=unique_by_group["saturation_current"],
            resistance_series=unique_by_group["resistance_series"],
            resistance_shunt=unique_by_group["resistance_shunt"],
            nNsVth=unique_by_group["nNsVth"],
            method="lambertw",
        )

        iv_curve = pd.DataFrame(
            {
                "_unique_id": unique_by_group["_unique_id"],
                "p_mp": iv_curve_raw["p_mp"],
                "i_mp": iv_curve_raw["i_mp"],
                "v_mp": iv_curve_raw["v_mp"],
                "i_sc": iv_curve_raw["i_sc"],
                "v_oc": iv_curve_raw["v_oc"],
            }
        )

        outputs = pd.merge(
            left=inputs,
            right=iv_curve,
            on="_unique_id",
            how="left",
        )

        self.p_mp = StringMetTimeSeries(outputs.loc[:, "p_mp"])
        self.i_mp = StringMetTimeSeries(outputs.loc[:, "i_mp"])
        self.v_mp = StringMetTimeSeries(outputs.loc[:, "v_mp"])
        self.i_sc = StringMetTimeSeries(outputs.loc[:, "i_sc"])
        self.v_oc = StringMetTimeSeries(outputs.loc[:, "v_oc"])
