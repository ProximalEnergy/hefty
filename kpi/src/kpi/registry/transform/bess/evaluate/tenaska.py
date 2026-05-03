import pandas as pd
import xarray as xr
from kpi.base.enumeration import NEW_NAME, TimeCoords
from kpi.base.protocol import CalcProtocol
from kpi.domain.agg.resample import resample_first, resample_sum
from kpi.domain.util import sum_arrays
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.arg import Required, Time15MinUtc
from kpi.op.transform.method import calc_field, method_calc
from kpi.registry.download.tenaska.generator import DownloadTenaskaGenerator as Gen
from kpi.registry.download.tenaska.virtual import DownloadTenaskaVirtual as Virtual


class TransformBessEvaluateTenaska(FieldRegistry[CalcProtocol]):
    @method_calc(
        time_15m_utc=Time15MinUtc(),
    )
    def hour_utc_15m(
        time_15m_utc: pd.DatetimeIndex,
    ) -> xr.DataArray:
        hourly = time_15m_utc.floor("h").astype("datetime64[ns]")

        return xr.DataArray(
            hourly,
            dims=[TimeCoords.TIME_15MIN_UTC.value],
            coords={TimeCoords.TIME_15MIN_UTC.value: time_15m_utc},
            attrs={
                NEW_NAME: TimeCoords.HOUR_UTC.value,
            },
        )

    # =======================================================
    # Convert day-ahead fields to hourly
    # =======================================================

    day_ahead_energy_charge_usd_h = calc_field(resample_first)(
        x=Required(Gen.day_ahead_energy_charge_raw_usd_15m),
        grouper=Required(hour_utc_15m),
    )

    day_ahead_energy_payment_usd_h = calc_field(resample_first)(
        x=Required(Gen.day_ahead_energy_payment_raw_usd_15m),
        grouper=Required(hour_utc_15m),
    )

    procured_capacity_reg_up_usd_h = calc_field(resample_first)(
        x=Required(Gen.procured_capacity_reg_up_raw_usd_15m),
        grouper=Required(hour_utc_15m),
    )

    procured_capacity_reg_down_usd_h = calc_field(resample_first)(
        x=Required(Gen.procured_capacity_reg_down_raw_usd_15m),
        grouper=Required(hour_utc_15m),
    )

    procured_capacity_responsive_reserve_usd_h = calc_field(resample_first)(
        x=Required(Gen.procured_capacity_responsive_reserve_raw_usd_15m),
        grouper=Required(hour_utc_15m),
    )

    procured_capacity_non_spin_usd_h = calc_field(resample_first)(
        x=Required(Gen.procured_capacity_non_spin_raw_usd_15m),
        grouper=Required(hour_utc_15m),
    )

    procured_capacity_ercot_contingency_reserve_usd_h = calc_field(resample_first)(
        x=Required(Gen.procured_capacity_ercot_contingency_reserve_raw_usd_15m),
        grouper=Required(hour_utc_15m),
    )

    virtual_day_ahead_energy_payment_usd_h = calc_field(resample_first)(
        x=Required(Virtual.virtual_day_ahead_energy_payment_raw_usd_15m),
        grouper=Required(hour_utc_15m),
    )

    # =======================================================
    # For real-time fields, get hourly totals by summing
    # =======================================================

    real_time_energy_imbalance_usd_h = calc_field(resample_sum)(
        x=Required(Gen.real_time_energy_imbalance_raw_usd_15m),
        grouper=Required(hour_utc_15m),
    )

    base_point_deviation_usd_h = calc_field(resample_sum)(
        x=Required(Gen.base_point_deviation_raw_usd_15m),
        grouper=Required(hour_utc_15m),
    )

    set_point_deviation_usd_h = calc_field(resample_sum)(
        x=Required(Gen.set_point_deviation_raw_usd_15m),
        grouper=Required(hour_utc_15m),
    )

    real_time_reliability_deployment_imbalance_usd_h = calc_field(resample_sum)(
        x=Required(Gen.real_time_reliability_deployment_imbalance_raw_usd_15m),
        grouper=Required(hour_utc_15m),
    )

    real_time_reg_up_imbalance_usd_h = calc_field(resample_sum)(
        x=Required(Gen.real_time_reg_up_imbalance_raw_usd_15m),
        grouper=Required(hour_utc_15m),
    )

    real_time_responsive_reserve_imbalance_usd_h = calc_field(resample_sum)(
        x=Required(Gen.real_time_responsive_reserve_imbalance_raw_usd_15m),
        grouper=Required(hour_utc_15m),
    )

    real_time_non_spin_imbalance_usd_h = calc_field(resample_sum)(
        x=Required(Gen.real_time_non_spin_imbalance_raw_usd_15m),
        grouper=Required(hour_utc_15m),
    )

    real_time_ercot_contingency_reserve_imbalance_usd_h = calc_field(resample_sum)(
        x=Required(Gen.real_time_ercot_contingency_reserve_imbalance_raw_usd_15m),
        grouper=Required(hour_utc_15m),
    )

    time_weighted_telemetered_generation_mwh_h = calc_field(resample_sum)(
        x=Required(Gen.time_weighted_telemetered_generation_raw_mwh_15m),
        grouper=Required(hour_utc_15m),
    )

    virtual_real_time_energy_imbalance_usd_h = calc_field(resample_sum)(
        x=Required(Virtual.virtual_real_time_energy_imbalance_raw_usd_15m),
        grouper=Required(hour_utc_15m),
    )

    # =======================================================
    # Calculate totals
    # =======================================================

    day_ahead_arbitrage_usd_h = calc_field(sum_arrays)(
        Required(day_ahead_energy_charge_usd_h),
        Required(day_ahead_energy_payment_usd_h),
    )

    day_ahead_ancillary_services_usd_h = calc_field(sum_arrays)(
        Required(procured_capacity_reg_up_usd_h),
        Required(procured_capacity_reg_down_usd_h),
        Required(procured_capacity_responsive_reserve_usd_h),
        Required(procured_capacity_non_spin_usd_h),
        Required(procured_capacity_ercot_contingency_reserve_usd_h),
    )

    real_time_ancillary_services_usd_h = calc_field(sum_arrays)(
        Required(real_time_reg_up_imbalance_usd_h),
        Required(real_time_reliability_deployment_imbalance_usd_h),
        Required(real_time_responsive_reserve_imbalance_usd_h),
        Required(real_time_non_spin_imbalance_usd_h),
        Required(real_time_ercot_contingency_reserve_imbalance_usd_h),
    )

    misc_charges_usd_h = calc_field(sum_arrays)(
        Required(base_point_deviation_usd_h),
        Required(set_point_deviation_usd_h),
    )

    virtual_net_usd_h = calc_field(sum_arrays)(
        Required(virtual_real_time_energy_imbalance_usd_h),
        Required(virtual_day_ahead_energy_payment_usd_h),
    )

    physical_total_usd_h = calc_field(sum_arrays)(
        Required(day_ahead_arbitrage_usd_h),
        Required(real_time_energy_imbalance_usd_h),
        Required(day_ahead_ancillary_services_usd_h),
        Required(real_time_ancillary_services_usd_h),
        Required(misc_charges_usd_h),
    )
