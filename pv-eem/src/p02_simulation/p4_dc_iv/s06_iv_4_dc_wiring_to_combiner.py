from dataclasses import dataclass
from enum import StrEnum

from interfaces import Indeces, ModuleEquipmentSeries, StringMetTimeSeries, SystemSeries
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation.p4_dc_iv.s05_iv_3_string import StringIVCurve


class ModelDCWiringToCombiner(StrEnum):
    """ModelDCWiringToCombiner."""

    FIXED = "fixed"
    TARGET_STC = "target_stc"


@dataclass(init=False, slots=True)
class IVafterDCWiring:
    """IVafterDCWiring."""

    i_mp: StringMetTimeSeries
    v_mp: StringMetTimeSeries
    i_sc: StringMetTimeSeries
    v_oc: StringMetTimeSeries

    # inputs into the next function
    _module_i_mp_stc: StringMetTimeSeries
    _string_p_mp_stc: StringMetTimeSeries

    def __init__(
        self,
        *,
        model: ModelDCWiringToCombiner,
        indeces: Indeces,
        modules_per_string: SystemSeries,
        dc_line_to_combiner_stc: SystemSeries,
        module_id_by_string: SystemSeries,
        string_iv_curve: StringIVCurve,
        imp_module_STC: ModuleEquipmentSeries,
        vmp_module_STC: ModuleEquipmentSeries,
    ):
        """Calc DC wiring loss as a percentage of loss at STC
        uses solarfarmer formula
        """
        # --- CONSTANTS ---
        LOSS_AT_STC = 1.5  # [%]

        # --- MERGE ---
        inputs = merge_by_dimension(
            data_series=[
                module_id_by_string,
                modules_per_string,
                dc_line_to_combiner_stc,
                string_iv_curve.v_mp,  # StringMetTimeSeries
                string_iv_curve.i_mp,
                string_iv_curve.v_oc,
                string_iv_curve.i_sc,
                imp_module_STC,
                vmp_module_STC,
            ],
            indeces=indeces,
            merge_how=MergeHow.LEFT,
        )

        # --- PASS THROUGH CALCULATIONS (For next step)
        inputs["string_v_mp_stc"] = (
            inputs["modules_per_string"] * inputs["module_v_mp_stc"]
        )
        inputs["string_p_mp_stc"] = (
            inputs["string_v_mp_stc"] * inputs["module_i_mp_stc"]
        )

        # --- INTERMEDIATE CALCULATIONS ---
        match model:
            case ModelDCWiringToCombiner.FIXED:
                inputs["loss_at_stc"] = LOSS_AT_STC / 100.0

            case ModelDCWiringToCombiner.TARGET_STC:
                inputs["loss_at_stc"] = inputs["dc_line_to_combiner_stc"] / 100.0

        # Ratio of in-situ current to STC current
        inputs["i_mp_ratio"] = inputs["i_mp"] / inputs["module_i_mp_stc"]
        inputs["loss_in_situ"] = inputs["i_mp_ratio"] * inputs["loss_at_stc"]

        # --- CALCULATIONS ---
        # recalculate power and voltage
        inputs["p_mp"] = inputs["string_v_mp"] * inputs["i_mp"]
        inputs["p_mp_recalculated"] = (
            inputs["p_mp"]  #
            * (1 - inputs["loss_in_situ"])
        )
        inputs["v_mp_adjusted"] = inputs["p_mp_recalculated"] / inputs["i_mp"]
        inputs["v_oc_adjusted"] = inputs["string_v_oc"] * (
            inputs["v_mp_adjusted"] / inputs["string_v_mp"]
        )

        # --- ASSIGN OUTPUTS ---
        # Pass through (no changes)
        self.i_sc = string_iv_curve.i_sc
        self.i_mp = string_iv_curve.i_mp

        # Calculated
        self.v_mp = StringMetTimeSeries(
            inputs.loc[:, "v_mp_adjusted"].rename("string_v_mp")
        )
        self.v_oc = StringMetTimeSeries(
            inputs.loc[:, "v_oc_adjusted"].rename("string_v_oc")
        )

        # Next Step
        self._module_i_mp_stc = StringMetTimeSeries(inputs.loc[:, "module_i_mp_stc"])
        self._string_p_mp_stc = StringMetTimeSeries(inputs.loc[:, "string_p_mp_stc"])
