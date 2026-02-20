from dataclasses import dataclass

import pandas as pd
from interfaces import (
    Indeces,
    TransformerDeviceSeries,
    TransformerTimeIndex,
    TransformerTimeSeries,
)
from p02_simulation._utils.aggregate_tier_codes import combine_unique_codes
from p02_simulation.p6_transformer.s00_ac_wiring_to_transformer import (
    TransformerWiring,
)


@dataclass(init=False, slots=True)
class TransformerInput:
    """TransformerInput."""

    power: TransformerTimeSeries
    device_ids: TransformerTimeSeries
    equipment_ids: TransformerTimeSeries
    tier: TransformerTimeSeries
    tier_codes: TransformerTimeSeries

    def __init__(
        self,
        *,
        indeces: Indeces,
        power_after_wiring: TransformerWiring,
        transformer_device_ids: TransformerDeviceSeries,
        transformer_equipment_ids: TransformerDeviceSeries,
    ):
        """Combine inverters by transformer, combines don't use merge_by_dimension"""
        # --- Unique Mapping of Transformers to Inverters ---
        unique_mapping = pd.concat(
            [
                indeces.inverter_device_index,
                transformer_device_ids,
                transformer_equipment_ids,
            ],
            axis=1,
        ).drop_duplicates()

        # --- Power Series ---
        input_power = pd.concat(
            [
                indeces.inverter_time_index.loc[:, "time"],
                indeces.inverter_time_index.loc[:, "pcs_device_id"],
                power_after_wiring.power,
                power_after_wiring.tier,
                power_after_wiring.tier_codes,
            ],
            axis=1,
        )

        # --- MERGE ---
        inputs = pd.merge(
            left=input_power,
            right=unique_mapping,
            on=["pcs_device_id"],
            how="left",
        )

        transformers = (
            inputs.groupby(["time", "transformer_device_id"])
            .agg(
                {
                    "p_mp": "sum",
                    "tier": "max",
                    "tier_codes": combine_unique_codes,
                    "transformer_equipment_id": "first",
                }
            )
            .reset_index()
        )

        self.power = TransformerTimeSeries(transformers.loc[:, "p_mp"])
        self.tier = TransformerTimeSeries(transformers.loc[:, "tier"])
        self.tier_codes = TransformerTimeSeries(transformers.loc[:, "tier_codes"])
        self.equipment_ids = TransformerTimeSeries(
            transformers.loc[:, "transformer_equipment_id"]
        )
        self.device_ids = TransformerTimeSeries(
            transformers.loc[:, "transformer_device_id"]
        )

        indeces.transformer_time_index = TransformerTimeIndex(
            pd.concat(
                [
                    transformers.loc[:, "time"],
                    transformers.loc[:, "transformer_device_id"],
                ],
                axis=1,
            )
        )
