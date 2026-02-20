from dataclasses import dataclass
from enum import StrEnum

import pandas as pd
from interfaces import Indeces, StringMetTimeSeries, SystemSeries
from p01_get_data.source_proximal.s09_get_module_data import Module
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation.p4_dc_iv.s02b_pv_watts_dc import PVWattsModel
from p02_simulation.p4_dc_iv.s03_iv_1_module import SingleDiodeModel


class ModelDegradation(StrEnum):
    """ModelDegradation."""

    NONE = "none"
    WARRANTED = "warranted"


@dataclass(init=False, slots=True)
class IVafterDegradation:
    """IVafterDegradation."""

    i_mp: StringMetTimeSeries
    v_mp: StringMetTimeSeries
    i_sc: StringMetTimeSeries
    v_oc: StringMetTimeSeries

    def __init__(
        self,
        *,
        model: ModelDegradation,
        indeces: Indeces,
        cod: str,
        module_id_by_string: SystemSeries,
        modules: Module,
        iv_curve: SingleDiodeModel | PVWattsModel,
    ):
        """Calculate the warranted degradation.  Currently this is
        only calculated on the current and voltage as if they
        contribute to degradation equally.  This is of course
        not true since degradation can be a function of current
        and voltage asymetrically.
        """
        # --- CONSTANTS ---
        DAYS_PER_YEAR = 365.2425  # days per year accounting for leap
        CURRENT_DEG_FACTOR = 0.5  # current contribution to degradation in [%]
        VOLTAGE_DEG_FACTOR = 0.5  # voltage contribution to degradation in [%]

        # --- MERGE ---
        match model:
            case ModelDegradation.NONE:
                self.i_mp = iv_curve.i_mp
                self.v_mp = iv_curve.v_mp
                self.i_sc = iv_curve.i_sc
                self.v_oc = iv_curve.v_oc

            case ModelDegradation.WARRANTED:
                # --- MERGE ---
                # This is just done to use the StringMetTimeSeries
                # in the merge

                inputs = merge_by_dimension(
                    data_series=[
                        iv_curve.i_mp,
                        iv_curve.v_mp,
                        iv_curve.i_sc,
                        iv_curve.v_oc,
                        module_id_by_string,
                        modules.warranted_degradation_rate,
                        modules.warranted_degradation_initial,
                    ],
                    indeces=indeces,
                    merge_how=MergeHow.LEFT,
                )

                # --- CALCULATE TIME SINCE COD ---
                if cod is None:
                    raise ValueError("cod in operational.projects must not be null")

                cod_timestamp = pd.to_datetime(cod).normalize()
                time_normalized = inputs["time"].dt.tz_localize(None).dt.normalize()
                time_delta = time_normalized - cod_timestamp
                inputs["delta_days"] = time_delta.dt.days

                # --- CALCULATE DEGRADATION ---
                # THIS IS WRONG, CURRENT AND VOLTAGE WILL NOT MULTIPLY TO
                for param in ["i_mp", "v_mp", "i_sc", "v_oc"]:
                    match param:
                        case "i_mp":
                            degradation_factor = CURRENT_DEG_FACTOR
                        case "v_mp":
                            degradation_factor = VOLTAGE_DEG_FACTOR
                        case "i_sc":
                            degradation_factor = CURRENT_DEG_FACTOR
                        case "v_oc":
                            degradation_factor = VOLTAGE_DEG_FACTOR
                        case _:
                            raise ValueError(f"Unknown param {param}")

                    initial_degradation = inputs[param] * (
                        inputs["warranted_degradation_initial"] / 100.0
                    )
                    elapsed_degradation = (
                        inputs[param]
                        * (inputs["warranted_degradation_rate"] / 100.0 / DAYS_PER_YEAR)
                        * inputs["delta_days"]
                    )

                    inputs[param] = (
                        inputs[param]
                        - initial_degradation * degradation_factor
                        - elapsed_degradation * degradation_factor
                    )

                # --- SET ATTRIBUTES ---a
                self.i_mp = StringMetTimeSeries(inputs.loc[:, "i_mp"])
                self.v_mp = StringMetTimeSeries(inputs.loc[:, "v_mp"])
                self.i_sc = StringMetTimeSeries(inputs.loc[:, "i_sc"])
                self.v_oc = StringMetTimeSeries(inputs.loc[:, "v_oc"])
