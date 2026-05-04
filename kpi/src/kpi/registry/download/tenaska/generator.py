from kpi.op.download.tenaska import (
    TenaskaModel,
    tenaska_field,
)
from kpi.op.field_registry import FieldRegistry


class DownloadTenaskaGenerator(FieldRegistry[TenaskaModel]):
    day_ahead_energy_payment_raw_usd_15m = tenaska_field("DAESAMT", scale=-1)

    day_ahead_energy_charge_raw_usd_15m = tenaska_field("DAEPAMT", scale=-1)

    real_time_energy_imbalance_raw_usd_15m = tenaska_field("RTEIAMT", scale=-1)

    base_point_deviation_raw_usd_15m = tenaska_field("BPDAMT", scale=-1)

    set_point_deviation_raw_usd_15m = tenaska_field("SPDAMT", scale=-1)

    real_time_reliability_deployment_imbalance_raw_usd_15m = tenaska_field(
        "RTRDASIAMT", scale=-1
    )

    procured_capacity_reg_up_raw_usd_15m = tenaska_field("PCRUAMT", scale=-1)

    procured_capacity_reg_down_raw_usd_15m = tenaska_field("PCRDAMT", scale=-1)

    procured_capacity_responsive_reserve_raw_usd_15m = tenaska_field(
        "PCRRAMT", scale=-1
    )

    procured_capacity_non_spin_raw_usd_15m = tenaska_field("PCNSAMT", scale=-1)

    procured_capacity_ercot_contingency_reserve_raw_usd_15m = tenaska_field(
        "PCECRAMT", scale=-1
    )

    real_time_reg_up_imbalance_raw_usd_15m = tenaska_field("RTRRUIMBAMT", scale=-1)

    real_time_responsive_reserve_imbalance_raw_usd_15m = tenaska_field(
        "RTRRIMBAMT", scale=-1
    )

    real_time_non_spin_imbalance_raw_usd_15m = tenaska_field("RTNSIMBAMT", scale=-1)

    real_time_ercot_contingency_reserve_imbalance_raw_usd_15m = tenaska_field(
        "RTECRIMBAMT", scale=-1
    )
