from dataclasses import dataclass

from interfaces import Indeces, StringMetTimeSeries, SystemSeries
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation.p4_dc_iv.s04_iv_2_warranted_degradation import IVafterDegradation


@dataclass(init=False, slots=True)
class StringIVCurve:
    """StringIVCurve."""

    v_mp: StringMetTimeSeries
    i_mp: StringMetTimeSeries
    v_oc: StringMetTimeSeries
    i_sc: StringMetTimeSeries

    def __init__(
        self,
        *,
        indeces: Indeces,
        modules_per_string: SystemSeries,
        iv_after_degradation: IVafterDegradation,
    ):
        """Calculate IV Curve at String level"""
        # --- MERGE ---

        merged_data = merge_by_dimension(
            data_series=[
                modules_per_string,
                iv_after_degradation.v_mp,
                iv_after_degradation.i_mp,
                iv_after_degradation.v_oc,
                iv_after_degradation.i_sc,
            ],
            indeces=indeces,
            merge_how=MergeHow.LEFT,
        )

        # --- CALCULATIONS ---
        # Scale voltage parameters by modules_per_string
        merged_data["string_v_oc"] = (
            merged_data["v_oc"] * merged_data["modules_per_string"]
        )
        merged_data["string_v_mp"] = (
            merged_data["v_mp"] * merged_data["modules_per_string"]
        )

        # --- ASSIGN OUTPUTS ---
        # Pass through
        self.i_mp = iv_after_degradation.i_mp
        self.i_sc = iv_after_degradation.i_sc

        # Calculated
        self.v_oc = StringMetTimeSeries(merged_data.loc[:, "string_v_oc"])
        self.v_mp = StringMetTimeSeries(merged_data.loc[:, "string_v_mp"])
