import pandas as pd
from interfaces import TimeSeries
from p02_simulation.p8_poi.s00_combine_poi import ProjectPowerBeforeClipping


class ProjectPowerAfterClipping:
    """ProjectPowerAfterClipping."""

    power: TimeSeries
    tier: TimeSeries
    tier_codes: TimeSeries

    def __init__(
        self,
        *,
        power_before_clipping: ProjectPowerBeforeClipping,
        poi_limit: float,
    ):
        """Calc the point of interconnection limit"""
        # poi limit is stored in MW but we need to convert it to W
        poi_limit = poi_limit * 1_000_000

        # clipping operation
        power_with_upper_limit = power_before_clipping.power.clip(
            upper=poi_limit,
            lower=0.0,
        )

        # replace all zero values with NaN
        power_without_zero_values = power_with_upper_limit.replace(0, pd.NA)

        # --- Assignments ---
        self.power = TimeSeries(power_without_zero_values)
        self.tier = power_before_clipping.tier
        self.tier_codes = power_before_clipping.tier_codes
