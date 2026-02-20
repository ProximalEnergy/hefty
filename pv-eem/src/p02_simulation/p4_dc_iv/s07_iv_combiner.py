from dataclasses import dataclass

import pandas as pd
from interfaces import (
    CombinerDeviceSeries,
    CombinerTimeIndex,
    CombinerTimeSeries,
    Indeces,
    ModuleEquipmentSeries,
    QualityAssurance,
    SystemSeries,
)
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation.p4_dc_iv.s06_iv_4_dc_wiring_to_combiner import IVafterDCWiring


@dataclass(init=False, slots=True)
class IVatCombiner:
    # power time series
    """IVatCombiner."""

    p_mp: CombinerTimeSeries
    i_mp: CombinerTimeSeries
    v_mp: CombinerTimeSeries
    i_sc: CombinerTimeSeries
    v_oc: CombinerTimeSeries

    # quality assurance
    tier: CombinerTimeSeries
    tier_codes: CombinerTimeSeries

    # pass throughs for later calculations
    _i_mp_array_stc: CombinerTimeSeries
    _dc_line_to_inverter_stc: CombinerTimeSeries

    def __init__(
        self,
        *,
        indeces: Indeces,
        quality_assurance: QualityAssurance,
        iv_after_wiring: IVafterDCWiring,
        combiner_device_id: SystemSeries | CombinerDeviceSeries,
        strings_per_combiner: SystemSeries,
        module_id_by_string: SystemSeries,
        dc_line_to_inverter_stc: SystemSeries,
        module_i_mp_stc: ModuleEquipmentSeries,
    ):
        """Calc IV Curve at Combiner level
        Caveat:
            - We are combining IV curves in this way (which is incorrect)
            because it would take too much memory to create hundreds of data points
            along each IV curve for each unique string.  This method will
            under-estimate the amount of string level mismatch for systems
            that are designed poorly and have very different IV curves
            for a given combiner.
            - One method that could be employed to solve this issue of memory
            is to work with polars or to append to a working iv curve in a
            row-wise fashion.  This would be slower but more accurate.
        """
        # --- MERGE ---
        inputs = merge_by_dimension(
            data_series=[
                combiner_device_id,
                strings_per_combiner,
                module_id_by_string,
                module_i_mp_stc,
                iv_after_wiring._string_p_mp_stc,
                iv_after_wiring.i_mp,
                iv_after_wiring.i_sc,
                iv_after_wiring.v_oc,
                iv_after_wiring.v_mp,
                quality_assurance.tier,
                quality_assurance.tier_codes,
                dc_line_to_inverter_stc,
            ],
            indeces=indeces,
            merge_how=MergeHow.LEFT,
        )
        # --- FUNCTION ---
        # Combine like strings
        for param in ["i_sc", "i_mp", "module_i_mp_stc"]:
            inputs[param] = inputs[param] * inputs["strings_per_combiner"]

        # Pre-compute weighted voltages
        inputs["v_mp_weighted"] = inputs["string_v_mp"] * inputs["string_p_mp_stc"]
        inputs["v_oc_weighted"] = inputs["string_v_oc"] * inputs["string_p_mp_stc"]

        # Groupby and aggregate
        outputs = (
            inputs.groupby(["time", "combiner_device_id"])
            .agg(
                {
                    "i_mp": "sum",
                    "module_i_mp_stc": "sum",
                    "i_sc": "sum",
                    "v_mp_weighted": "sum",
                    "v_oc_weighted": "sum",
                    "string_p_mp_stc": "sum",  # Needed for final division
                    "tier": "max",
                    "tier_codes": "first",
                    "dc_line_to_inverter_stc": "first",
                }
            )
            .reset_index()
        )

        # Compute weighted averages
        outputs["v_mp"] = (
            outputs["v_mp_weighted"] / outputs["string_p_mp_stc"]
        ).fillna(0)
        outputs["v_oc"] = (
            outputs["v_oc_weighted"] / outputs["string_p_mp_stc"]
        ).fillna(0)

        # Drop intermediate columns
        # outputs = outputs.drop(
        #     columns=["v_mp_weighted", "v_oc_weighted", "P_array_stc"]

        # recalculate p_mp
        outputs["p_mp"] = outputs["v_mp"] * outputs["i_mp"]

        # --- Assignments ---
        self.p_mp = CombinerTimeSeries(outputs.loc[:, "p_mp"])
        self.i_mp = CombinerTimeSeries(outputs.loc[:, "i_mp"])
        self.v_mp = CombinerTimeSeries(outputs.loc[:, "v_mp"])
        self.i_sc = CombinerTimeSeries(outputs.loc[:, "i_sc"])
        self.v_oc = CombinerTimeSeries(outputs.loc[:, "v_oc"])

        # quality assurance
        self.tier = CombinerTimeSeries(outputs.loc[:, "tier"])
        self.tier_codes = CombinerTimeSeries(outputs.loc[:, "tier_codes"])

        # pass throughs for later calculations
        self._i_mp_array_stc = CombinerTimeSeries(outputs.loc[:, "module_i_mp_stc"])
        self._dc_line_to_inverter_stc = CombinerTimeSeries(
            outputs.loc[:, "dc_line_to_inverter_stc"]
        )

        # assign indeces
        indeces.combiner_time_index = CombinerTimeIndex(
            pd.concat(
                [
                    outputs.loc[:, "time"],
                    outputs.loc[:, "combiner_device_id"],
                ],
                axis=1,
            )
        )
