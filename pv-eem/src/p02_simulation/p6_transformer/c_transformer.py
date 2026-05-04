from interfaces import Indeces, TransformerDeviceSeries, TransformerTimeSeries
from p01_get_data.source_proximal.s09_get_inverter_data import PvEemInverter
from p02_simulation.p5_inverter.c_inverter import InverterPower
from p02_simulation.p6_transformer.s00_ac_wiring_to_transformer import (
    TransformerWiring,
)
from p02_simulation.p6_transformer.s01_combine_transformers import (
    TransformerInput,
)
from p02_simulation.p6_transformer.s02_transformer_efficiency import (
    TransformerEfficiency,
)


class TransformerPower:
    """TransformerPower."""

    time: TransformerTimeSeries
    power: TransformerTimeSeries
    device_ids: TransformerTimeSeries
    tier: TransformerTimeSeries
    tier_codes: TransformerTimeSeries

    def __init__(
        self,
        *,
        indeces: Indeces,
        power_at_inverter: InverterPower,
        inverters: PvEemInverter,
        transformer_device_ids: TransformerDeviceSeries,
        transformer_equipment_ids: TransformerDeviceSeries,
    ):
        """Calculate the power at each individual transformer"""
        # --- Wiring loss from inverter to transformer ---
        power_after_wiring = TransformerWiring(
            power_at_inverter=power_at_inverter,
            inverters=inverters,
        )

        # --- Combine transformers ---
        power_at_transformer_input = TransformerInput(
            indeces=indeces,
            power_after_wiring=power_after_wiring,
            transformer_device_ids=transformer_device_ids,
            transformer_equipment_ids=transformer_equipment_ids,
        )

        # --- Transformer Efficiency ---
        transformers_after_efficiency = TransformerEfficiency(
            power_at_transformer_input=power_at_transformer_input,
        )

        # --- Assignment for Export ---
        self.time = TransformerTimeSeries(indeces.transformer_time_index.loc[:, "time"])
        self.device_ids = TransformerTimeSeries(
            indeces.transformer_time_index.loc[:, "transformer_device_id"]
        )
        self.power = transformers_after_efficiency.power
        self.tier = transformers_after_efficiency.tier
        self.tier_codes = transformers_after_efficiency.tier_codes
