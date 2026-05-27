from kpi.base.enumeration import TimeCoord
from kpi.domain.agg.resample import resample_first, resample_sum
from kpi.domain.util import sum_arrays, time_grouper
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.arg import (
    TimeCoordArg,
    TimeCoordConstant,
    grouper,
    optional,
    required,
)
from kpi.op.transform.method import MethodCalc, calc_field
from kpi.registry.download.tenaska.generator import DownloadTenaskaGenerator as Gen
from kpi.registry.download.tenaska.virtual import DownloadTenaskaVirtual as Virtual


class TransformBessEvaluateTenaska(FieldRegistry[MethodCalc]):
    hour_utc_15m = calc_field(time_grouper)(
        from_time=TimeCoordArg(time_coord=TimeCoord.TIME_15MIN_UTC),
        from_time_coord=TimeCoordConstant(value=TimeCoord.TIME_15MIN_UTC),
        to_time_coord=TimeCoordConstant(value=TimeCoord.HOUR_UTC),
    )

    # =======================================================
    # Convert day-ahead fields to hourly
    # =======================================================

    day_ahead_energy_charge_usd_h = calc_field(resample_first)(
        x=required(Gen.day_ahead_energy_charge_raw_usd_15m),
        grouper=grouper(hour_utc_15m),
    )

    day_ahead_energy_payment_usd_h = calc_field(resample_first)(
        x=required(Gen.day_ahead_energy_payment_raw_usd_15m),
        grouper=grouper(hour_utc_15m),
    )

    procured_capacity_reg_up_usd_h = calc_field(resample_first)(
        x=required(Gen.procured_capacity_reg_up_raw_usd_15m),
        grouper=grouper(hour_utc_15m),
    )

    procured_capacity_reg_down_usd_h = calc_field(resample_first)(
        x=required(Gen.procured_capacity_reg_down_raw_usd_15m),
        grouper=grouper(hour_utc_15m),
    )

    procured_capacity_responsive_reserve_usd_h = calc_field(resample_first)(
        x=required(Gen.procured_capacity_responsive_reserve_raw_usd_15m),
        grouper=grouper(hour_utc_15m),
    )

    procured_capacity_non_spin_usd_h = calc_field(resample_first)(
        x=required(Gen.procured_capacity_non_spin_raw_usd_15m),
        grouper=grouper(hour_utc_15m),
    )

    procured_capacity_ercot_contingency_reserve_usd_h = calc_field(resample_first)(
        x=required(Gen.procured_capacity_ercot_contingency_reserve_raw_usd_15m),
        grouper=grouper(hour_utc_15m),
    )

    virtual_day_ahead_energy_payment_usd_h = calc_field(resample_first)(
        x=required(Virtual.virtual_day_ahead_energy_payment_raw_usd_15m),
        grouper=grouper(hour_utc_15m),
    )

    # =======================================================
    # For real-time fields, get hourly totals by summing
    # =======================================================

    real_time_energy_imbalance_usd_h = calc_field(resample_sum)(
        x=required(Gen.real_time_energy_imbalance_raw_usd_15m),
        grouper=grouper(hour_utc_15m),
    )

    base_point_deviation_usd_h = calc_field(resample_sum)(
        x=required(Gen.base_point_deviation_raw_usd_15m),
        grouper=grouper(hour_utc_15m),
    )

    set_point_deviation_usd_h = calc_field(resample_sum)(
        x=required(Gen.set_point_deviation_raw_usd_15m),
        grouper=grouper(hour_utc_15m),
    )

    real_time_reliability_deployment_imbalance_usd_h = calc_field(resample_sum)(
        x=required(Gen.real_time_reliability_deployment_imbalance_raw_usd_15m),
        grouper=grouper(hour_utc_15m),
    )

    real_time_reg_up_imbalance_usd_h = calc_field(resample_sum)(
        x=required(Gen.real_time_reg_up_imbalance_raw_usd_15m),
        grouper=grouper(hour_utc_15m),
    )

    real_time_responsive_reserve_imbalance_usd_h = calc_field(resample_sum)(
        x=required(Gen.real_time_responsive_reserve_imbalance_raw_usd_15m),
        grouper=grouper(hour_utc_15m),
    )

    real_time_non_spin_imbalance_usd_h = calc_field(resample_sum)(
        x=required(Gen.real_time_non_spin_imbalance_raw_usd_15m),
        grouper=grouper(hour_utc_15m),
    )

    real_time_ercot_contingency_reserve_imbalance_usd_h = calc_field(resample_sum)(
        x=required(Gen.real_time_ercot_contingency_reserve_imbalance_raw_usd_15m),
        grouper=grouper(hour_utc_15m),
    )

    virtual_real_time_energy_imbalance_usd_h = calc_field(resample_sum)(
        x=required(Virtual.virtual_real_time_energy_imbalance_raw_usd_15m),
        grouper=grouper(hour_utc_15m),
    )

    # =======================================================
    # Calculate totals
    # =======================================================

    day_ahead_arbitrage_usd_h = calc_field(sum_arrays)(
        optional(day_ahead_energy_charge_usd_h),
        optional(day_ahead_energy_payment_usd_h),
    )

    day_ahead_ancillary_services_usd_h = calc_field(sum_arrays)(
        optional(procured_capacity_reg_up_usd_h),
        optional(procured_capacity_reg_down_usd_h),
        optional(procured_capacity_responsive_reserve_usd_h),
        optional(procured_capacity_non_spin_usd_h),
        optional(procured_capacity_ercot_contingency_reserve_usd_h),
    )

    real_time_ancillary_services_usd_h = calc_field(sum_arrays)(
        optional(real_time_reg_up_imbalance_usd_h),
        optional(real_time_reliability_deployment_imbalance_usd_h),
        optional(real_time_responsive_reserve_imbalance_usd_h),
        optional(real_time_non_spin_imbalance_usd_h),
        optional(real_time_ercot_contingency_reserve_imbalance_usd_h),
    )

    misc_charges_usd_h = calc_field(sum_arrays)(
        optional(base_point_deviation_usd_h),
        optional(set_point_deviation_usd_h),
    )

    virtual_net_usd_h = calc_field(sum_arrays)(
        optional(virtual_real_time_energy_imbalance_usd_h),
        optional(virtual_day_ahead_energy_payment_usd_h),
    )

    physical_total_usd_h = calc_field(sum_arrays)(
        optional(day_ahead_arbitrage_usd_h),
        optional(real_time_energy_imbalance_usd_h),
        optional(day_ahead_ancillary_services_usd_h),
        optional(real_time_ancillary_services_usd_h),
        optional(misc_charges_usd_h),
    )
