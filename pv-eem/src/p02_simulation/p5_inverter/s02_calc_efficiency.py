from dataclasses import dataclass
from enum import StrEnum

import pvlib
from interfaces import Indeces, InverterTimeSeries
from p01_get_data.source_proximal.s09_get_inverter_data import Inverter
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation.p5_inverter.s01_combine_iv_curves import InverterInputTerminal


class ModelInverterEfficiency(StrEnum):
    """ModelInverterEfficiency."""

    SANDIA = "sandia"


@dataclass(init=False, slots=True)
class InverterPowerAfterEfficiency:
    """InverterPowerAfterEfficiency."""

    power: InverterTimeSeries
    current: InverterTimeSeries
    voltage: InverterTimeSeries
    tier: InverterTimeSeries
    tier_codes: InverterTimeSeries

    def __init__(
        self,
        *,
        model: ModelInverterEfficiency,
        indeces: Indeces,
        iv_inverters: InverterInputTerminal,
        inverters: Inverter,
    ):
        """Calculate inverter efficiency given:
        - inverter parameters
        - input DC iv curves
        """
        # --- Merge ---
        inputs = merge_by_dimension(
            data_series=[
                iv_inverters.v_mp,
                iv_inverters.p_mp,
                iv_inverters.equipment_ids,
            ],
            indeces=indeces,
            merge_how=MergeHow.LEFT,
        )

        match model:
            case ModelInverterEfficiency.SANDIA:
                for position_id, inverter_id in enumerate(inverters.pcs_equipment_id):
                    # Get the indices for this inverter before doing the calculation
                    target_indices = inputs.index[
                        inputs["pcs_equipment_id"] == inverter_id
                    ]

                    # Create a subset of the full dataset only related to this
                    # specific inverter equipment id
                    target_inverter = inputs.loc[
                        inputs["pcs_equipment_id"] == inverter_id
                    ]

                    # Calculate inverter power
                    inverter_power = pvlib.inverter.sandia(
                        v_dc=target_inverter["v_mp"],
                        p_dc=target_inverter["p_mp"],
                        inverter={
                            "Paco": inverters.power_ac_nominal.iloc[position_id],
                            "Pdco": inverters.power_dc_nominal.iloc[position_id],
                            "Vdco": inverters.voltage_dc_nominal.iloc[position_id],
                            "Pso": inverters.power_start_up.iloc[position_id],
                            "C0": inverters.c0.iloc[position_id],
                            "C1": inverters.c1.iloc[position_id],
                            "C2": inverters.c2.iloc[position_id],
                            "C3": inverters.c3.iloc[position_id],
                            "Pnt": inverters.night_tare.iloc[position_id],
                        },
                    )

                    # Use the pre-calculated indices for assignment
                    inputs.loc[target_indices, "p_mp"] = inverter_power.values
            case _:
                raise ValueError(f"Unknown inverter efficiency model: {model}")

        # --- Pass throughs ---
        self.tier = iv_inverters.tier
        self.tier_codes = iv_inverters.tier_codes

        # --- Assignments ---
        self.power = InverterTimeSeries(inputs.loc[:, "p_mp"])
        self.voltage = InverterTimeSeries(inputs.loc[:, "v_mp"])
        self.current = InverterTimeSeries(self.power / self.voltage)
