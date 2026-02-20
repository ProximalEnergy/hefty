from interfaces import CombinerTimeSeries
from p02_simulation.p4_dc_iv.s07_iv_combiner import IVatCombiner


class IVafterQC:
    """IVafterQC."""

    p_mp: CombinerTimeSeries
    i_mp: CombinerTimeSeries
    v_mp: CombinerTimeSeries
    i_sc: CombinerTimeSeries
    v_oc: CombinerTimeSeries

    # pass through for later calculations
    i_mp_array_stc: CombinerTimeSeries

    # quality assurance
    tier: CombinerTimeSeries
    tier_codes: CombinerTimeSeries

    def __init__(
        self,
        *,
        iv_at_combiner: IVatCombiner,
    ):
        """Perform quality control on the IV data.
        Filters values below 0 and sets them to zero.
        """
        # Create a mask for valid power (> 0)
        valid_power_mask = iv_at_combiner.p_mp > 0

        # Apply the mask to all electrical parameters
        self.p_mp = CombinerTimeSeries(iv_at_combiner.p_mp[valid_power_mask])
        self.i_mp = CombinerTimeSeries(iv_at_combiner.i_mp[valid_power_mask])
        self.v_mp = CombinerTimeSeries(iv_at_combiner.v_mp[valid_power_mask])
        self.i_sc = CombinerTimeSeries(iv_at_combiner.i_sc[valid_power_mask])
        self.v_oc = CombinerTimeSeries(iv_at_combiner.v_oc[valid_power_mask])

        # Apply same mask to other attributes
        self.tier = CombinerTimeSeries(iv_at_combiner.tier[valid_power_mask])
        self.tier_codes = CombinerTimeSeries(
            iv_at_combiner.tier_codes[valid_power_mask]
        )
        self._i_mp_array_stc = CombinerTimeSeries(
            iv_at_combiner._i_mp_array_stc[valid_power_mask]
        )
        self._dc_line_to_inverter_stc = CombinerTimeSeries(
            iv_at_combiner._dc_line_to_inverter_stc[valid_power_mask]
        )
