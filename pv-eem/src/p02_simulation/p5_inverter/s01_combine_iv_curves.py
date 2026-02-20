from dataclasses import dataclass

import pandas as pd
from interfaces import (
    CombinerDeviceSeries,
    Indeces,
    InverterDeviceSeries,
    InverterTimeIndex,
    InverterTimeSeries,
)
from p02_simulation._utils.aggregate_tier_codes import combine_unique_codes
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation.p5_inverter.s00_dc_wiring_to_inverter import InverterDCWires


@dataclass(init=False, slots=True)
class InverterInputTerminal:
    """InverterInputTerminal."""

    p_mp: InverterTimeSeries
    i_mp: InverterTimeSeries
    v_mp: InverterTimeSeries
    i_sc: InverterTimeSeries
    v_oc: InverterTimeSeries

    tier: InverterTimeSeries
    tier_codes: InverterTimeSeries

    equipment_ids: InverterTimeSeries

    def __init__(
        self,
        *,
        indeces: Indeces,
        iv_combiners_wiring: InverterDCWires,
        inverter_equipment_ids: InverterDeviceSeries,
        inverter_device_ids: InverterDeviceSeries,
    ):
        """For each inverter, loop through child combiners
        and create a single IV curve

        The created IV curve will have a set number of points
        and fixed voltage intervals

        Caveats:
            - Note that even though the database has a inverter_module_device_id,
            we are only using the inverter_device_id here.
        """
        # --- Constants ---
        _NUM_POINTS = 100

        # We want to merge these on "combiner_device_id"
        # so we convert them to CombinerDeviceSeries
        inputs = merge_by_dimension(
            data_series=[
                iv_combiners_wiring.i_mp,
                iv_combiners_wiring.v_mp,
                iv_combiners_wiring.i_sc,
                iv_combiners_wiring.v_oc,
                iv_combiners_wiring.tier,
                iv_combiners_wiring.tier_codes,
                CombinerDeviceSeries(inverter_equipment_ids),
                CombinerDeviceSeries(inverter_device_ids),
            ],
            indeces=indeces,
            merge_how=MergeHow.LEFT,
        )

        inverters = (
            inputs.groupby(["time", "pcs_device_id"])
            .agg(
                {
                    "v_mp": "mean",
                    "v_oc": "mean",
                    "i_mp": "sum",
                    "i_sc": "sum",
                    "tier": "max",
                    "tier_codes": combine_unique_codes,
                    "pcs_equipment_id": "first",
                }
            )
            .reset_index()
        )
        inverters["p_mp"] = InverterTimeSeries(
            (inverters["i_mp"] * inverters["v_mp"]).rename("p_mp")
        )

        # --- Assignment ---
        self.p_mp = InverterTimeSeries(inverters.loc[:, "p_mp"])
        self.i_mp = InverterTimeSeries(inverters.loc[:, "i_mp"])
        self.v_mp = InverterTimeSeries(inverters.loc[:, "v_mp"])
        self.i_sc = InverterTimeSeries(inverters.loc[:, "i_sc"])
        self.v_oc = InverterTimeSeries(inverters.loc[:, "v_oc"])

        self.equipment_ids = InverterTimeSeries(inverters.loc[:, "pcs_equipment_id"])

        self.tier = InverterTimeSeries(inverters.loc[:, "tier"])
        self.tier_codes = InverterTimeSeries(inverters.loc[:, "tier_codes"])

        indeces.inverter_time_index = InverterTimeIndex(
            pd.concat(
                [
                    inverters.loc[:, "time"],
                    inverters.loc[:, "pcs_device_id"],
                ],
                axis=1,
            )
        )
