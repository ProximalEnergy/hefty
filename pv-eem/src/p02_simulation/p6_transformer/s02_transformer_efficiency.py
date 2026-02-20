from dataclasses import dataclass

from interfaces import TransformerTimeSeries
from p02_simulation.p6_transformer.s01_combine_transformers import (
    TransformerInput,
)
from pvlib.transformer import simple_efficiency


@dataclass(init=False, slots=True)
class TransformerEfficiency:
    """TransformerEfficiency."""

    power: TransformerTimeSeries
    tier: TransformerTimeSeries
    tier_codes: TransformerTimeSeries
    device_ids: TransformerTimeSeries

    def __init__(self, *, power_at_transformer_input: TransformerInput):
        """Calculate the power at each individual transformer"""
        # --- HARCODED Values ---
        NO_LOAD_LOSS = 0.2  # [%]
        LOAD_LOSS = 0.7  # [%]

        # --- Intermediate Calculations ---
        no_load_loss = NO_LOAD_LOSS / 100.0
        load_loss = LOAD_LOSS / 100.0

        # --- Calculate Transformer Efficiency ---
        power_after_efficiency = simple_efficiency(
            input_power=power_at_transformer_input.power,
            no_load_loss=no_load_loss,
            load_loss=load_loss,
            transformer_rating=3600000,
        )

        self.power = TransformerTimeSeries(power_after_efficiency)
        self.tier = power_at_transformer_input.tier
        self.tier_codes = power_at_transformer_input.tier_codes
        self.device_ids = power_at_transformer_input.device_ids
