from dataclasses import dataclass
from enum import StrEnum

from interfaces import CombinerTimeSeries, Indeces
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation.p4_dc_iv.c_dc_iv import PowerAtCombiner


class ModelDCWiringToInverter(StrEnum):
    """ModelDCWiringToInverter."""

    FIXED = "fixed"
    TARGET_STC = "target_stc"


@dataclass(init=False, slots=True)
class InverterDCWires:
    """InverterDCWires."""

    i_mp: CombinerTimeSeries
    v_mp: CombinerTimeSeries
    i_sc: CombinerTimeSeries
    v_oc: CombinerTimeSeries
    tier: CombinerTimeSeries
    tier_codes: CombinerTimeSeries

    def __init__(
        self,
        *,
        model: ModelDCWiringToInverter,
        indeces: Indeces,
        power_at_combiner: PowerAtCombiner,
    ):
        """Calc DC wiring loss as a percentage of loss at STC.  Losses are calculated
        as in solarfarmer documentation
        """
        # --- CONSTANTS ---
        LOSS_AT_STC = 0.25  # [%]

        # --- MERGE ---
        inputs = merge_by_dimension(
            data_series=[
                power_at_combiner._i_mp_array_stc,  # CombinerTimeSeries
                power_at_combiner._dc_line_to_inverter_stc,
                power_at_combiner.p_mp,
                power_at_combiner.i_mp,
                power_at_combiner.i_sc,
                power_at_combiner.v_oc,
                power_at_combiner.tier,
                power_at_combiner.tier_codes,
            ],
            indeces=indeces,
            merge_how=MergeHow.LEFT,
        )

        # --- INTERMEDIATE CALCULATIONS ---
        # Array parameters at STC
        match model:
            case ModelDCWiringToInverter.FIXED:
                inputs["loss_at_stc"] = LOSS_AT_STC / 100.0
            case ModelDCWiringToInverter.TARGET_STC:
                inputs["loss_at_stc"] = inputs["dc_line_to_inverter_stc"] / 100.0

        # Ratio of in-situ power to STC power
        inputs["i_mp_ratio"] = inputs["i_mp"] / inputs["module_i_mp_stc"]
        inputs["loss_in_situ"] = inputs["i_mp_ratio"] * inputs["loss_at_stc"]

        # --- Calculations ---
        # recalculate power and voltage
        inputs["p_mp_recalculated"] = (
            inputs["p_mp"]  #
            * (1 - inputs["loss_in_situ"])
        )
        inputs["v_mp"] = inputs["p_mp_recalculated"] / inputs["i_mp"]

        # --- Assignments ---
        self.i_mp = CombinerTimeSeries(inputs.loc[:, "i_mp"])
        self.v_mp = CombinerTimeSeries(inputs.loc[:, "v_mp"])
        self.i_sc = power_at_combiner.i_sc
        self.v_oc = power_at_combiner.v_oc

        self.tier = power_at_combiner.tier
        self.tier_codes = power_at_combiner.tier_codes
