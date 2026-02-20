from dataclasses import dataclass

import pandas as pd
from interfaces import Indeces, StringMetTimeSeries, SystemSeries
from p01_get_data.source_proximal.s09_get_module_data import Module
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation._utils.data_factorizer import factorize


@dataclass(init=False, slots=True)
class PVWattsModel:
    """PVWattsModel."""

    p_mp: StringMetTimeSeries
    i_mp: StringMetTimeSeries
    v_mp: StringMetTimeSeries
    i_sc: StringMetTimeSeries
    v_oc: StringMetTimeSeries

    def __init__(
        self,
        *,
        indeces: Indeces,
        module_id_by_string: SystemSeries,
        modules: Module,
        cell_temperature: StringMetTimeSeries,
        egpoai: StringMetTimeSeries,
    ):
        # --- CONSTANTS ---
        IRRAD_REF = 1000.0  # W/m^2
        TEMP_REF = 25.0  # C

        # --- MERGE ---
        inputs = merge_by_dimension(
            data_series=[
                module_id_by_string,
                modules.pmax,
                modules.imp,
                modules.isc,
                modules.vmp,
                modules.voc,
                modules.alpha_isc,
                modules.beta_voc,
                modules.gamma_pmax,
                cell_temperature,
                egpoai,
            ],
            indeces=indeces,
            merge_how=MergeHow.LEFT,
        )

        # --- FACTORIZE ---
        # Many of the parameters are unique to the pv_module_id
        inputs = factorize(
            dataframe=inputs,
            columns=["module_equipment_id", "global", "cell_temp"],
            rounding_precision=1,
        )

        unique_by_group = inputs.groupby("_unique_id").first()
        unique_by_group = unique_by_group.reset_index()

        # --- FUNCTION ---
        unique_by_group["delta_temp"] = unique_by_group["cell_temp"] - TEMP_REF
        temp_co_power = unique_by_group["gamma_pmax"] / 100

        unique_by_group["p_mp"] = (
            (unique_by_group["global"] / IRRAD_REF)
            * unique_by_group["module_p_max_stc"]
            * (1 + temp_co_power * unique_by_group["delta_temp"])
        )

        unique_by_group["i_mp"] = (
            (unique_by_group["global"] / IRRAD_REF)
            * unique_by_group["module_i_mp_stc"]
            * (1 + unique_by_group["alpha_isc"] * unique_by_group["delta_temp"])
        )

        unique_by_group["i_sc"] = (
            (unique_by_group["global"] / IRRAD_REF)
            * unique_by_group["module_i_sc_stc"]
            * (1 + unique_by_group["alpha_isc"] * unique_by_group["delta_temp"])
        )

        unique_by_group["v_mp"] = unique_by_group["p_mp"] / unique_by_group["i_mp"]
        unique_by_group["v_oc"] = unique_by_group["module_v_oc_stc"] * (
            1 + unique_by_group["beta_voc"] * unique_by_group["delta_temp"]
        )

        outputs = pd.merge(
            left=inputs,
            right=unique_by_group[
                ["_unique_id", "p_mp", "i_mp", "i_sc", "v_mp", "v_oc"]
            ],
            on="_unique_id",
            how="left",
        )

        _test = outputs[(outputs["string_id"] == 250) & (outputs["global"] > 0)]

        self.p_mp = StringMetTimeSeries(outputs.loc[:, "p_mp"])
        self.i_mp = StringMetTimeSeries(outputs.loc[:, "i_mp"])
        self.i_sc = StringMetTimeSeries(outputs.loc[:, "i_sc"])
        self.v_mp = StringMetTimeSeries(outputs.loc[:, "v_mp"])
        self.v_oc = StringMetTimeSeries(outputs.loc[:, "v_oc"])
