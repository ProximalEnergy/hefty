from dataclasses import dataclass

import pandas as pd
from interfaces import InverterTimeSeries
from p01_get_data.source_proximal.s09_get_inverter_data import Inverter
from p02_simulation.p5_inverter.c_inverter import InverterPower


@dataclass(init=False, slots=True)
class TransformerWiring:
    """TransformerWiring."""

    power: InverterTimeSeries
    inverter_device_ids: InverterTimeSeries
    tier: InverterTimeSeries
    tier_codes: InverterTimeSeries

    def __init__(
        self,
        *,
        power_at_inverter: InverterPower,
        inverters: Inverter,
    ):
        """Calculate the power loss in wire between inverter and transformer"""
        # --- Hard Coded ---
        LOSS_AT_FULL_POWER = 0.0  # [%]

        # --- Intermediate Calculations ---
        loss_at_full_power = LOSS_AT_FULL_POWER / 100.0

        # --- Losses by inverter ---
        inverter_params_df = pd.concat(
            [
                inverters.pcs_equipment_id,
                inverters.power_ac_nominal,
            ],
            axis=1,
        )

        power_at_inverter_df = pd.concat(
            [
                power_at_inverter.power,
                power_at_inverter.device_ids,
                power_at_inverter.equipment_ids,
            ],
            axis=1,
        )

        for target_inverter_id in inverters.pcs_equipment_id:
            target_inverter_params = inverter_params_df.loc[
                inverter_params_df["pcs_equipment_id"] == target_inverter_id
            ]
            target_max_power = target_inverter_params["power_ac_nominal"].iloc[0]

            # Get the data for the target inverter
            target_inverter = power_at_inverter_df.loc[
                power_at_inverter_df["pcs_equipment_id"] == target_inverter_id
            ]

            # Calculate the power loss in the wire
            target_inverter.loc[:, "wire_loss"] = (
                (target_inverter["p_mp"] ** 2) / target_max_power * loss_at_full_power
            )

            # Add the wire loss to the inverter
            target_inverter.loc[:, "p_mp"] = (
                target_inverter["p_mp"] - target_inverter["wire_loss"]
            )

            # Update the power values in the full inverters dataset
            power_at_inverter_df.loc[
                power_at_inverter_df["pcs_equipment_id"] == target_inverter_id, "p_mp"
            ] = target_inverter["p_mp"]

        self.power = InverterTimeSeries(power_at_inverter_df.loc[:, "p_mp"])
        self.inverter_device_ids = InverterTimeSeries(
            power_at_inverter_df.loc[:, "device_id"]
        )
        self.tier = power_at_inverter.tier
        self.tier_codes = power_at_inverter.tier_codes
