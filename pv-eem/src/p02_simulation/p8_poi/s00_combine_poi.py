from dataclasses import dataclass

from interfaces import Indeces, TimeSeries
from p02_simulation._utils.aggregate_tier_codes import combine_unique_codes
from p02_simulation._utils.data_combiner import MergeHow, merge_by_dimension
from p02_simulation.p6_transformer.c_transformer import TransformerPower


@dataclass(init=False, slots=True)
class ProjectPowerBeforeClipping:
    """ProjectPowerBeforeClipping."""

    power: TimeSeries
    tier: TimeSeries
    tier_codes: TimeSeries

    def __init__(
        self,
        *,
        indeces: Indeces,
        transformers: TransformerPower,
    ):
        """Calc the point of interconnection limit"""
        inputs = merge_by_dimension(
            data_series=[
                transformers.power,
                transformers.tier,
                transformers.tier_codes,
            ],
            indeces=indeces,
            merge_how=MergeHow.LEFT,
        )

        poi = (
            inputs.groupby(["time"])
            .agg(
                {
                    "p_mp": "sum",
                    "tier": "max",
                    "tier_codes": combine_unique_codes,
                }
            )
            .reset_index()
        )

        self.power = TimeSeries(poi.loc[:, "p_mp"])
        self.tier = TimeSeries(poi.loc[:, "tier"])
        self.tier_codes = TimeSeries(poi.loc[:, "tier_codes"])
