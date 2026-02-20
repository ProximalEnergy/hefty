from interfaces import Indeces, TimeSeries
from p02_simulation.p6_transformer.c_transformer import TransformerPower
from p02_simulation.p8_poi.s00_combine_poi import ProjectPowerBeforeClipping
from p02_simulation.p8_poi.s01_calc_poi_limit import ProjectPowerAfterClipping


class ProjectPower:
    """ProjectPower."""

    time: TimeSeries
    power: TimeSeries
    tier: TimeSeries
    tier_codes: TimeSeries

    def __init__(
        self,
        *,
        indeces: Indeces,
        power_at_transformer: TransformerPower,
        poi_limit: float,
    ):
        """Calc the point of interconnection"""
        power_before_clipping = ProjectPowerBeforeClipping(
            indeces=indeces,
            transformers=power_at_transformer,
        )

        power_after_clipping = ProjectPowerAfterClipping(
            power_before_clipping=power_before_clipping,
            poi_limit=poi_limit,
        )
        self.time = indeces.time_index
        self.power = power_after_clipping.power
        self.tier = power_after_clipping.tier
        self.tier_codes = power_after_clipping.tier_codes
