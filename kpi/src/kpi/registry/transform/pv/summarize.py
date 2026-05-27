import numpy as np
import pandas as pd
import xarray as xr
from core.enumerations import DeviceTypeEnum

from kpi.base.enumeration import TimeCoord
from kpi.base.util import coord
from kpi.domain.agg.across_devices import mean_across_devices, sum_across_devices
from kpi.domain.agg.other import (
    daily_mean_across_devices,
    daily_mean_across_grouped_devices,
)
from kpi.domain.agg.resample import resample_mean, resample_sum
from kpi.domain.module_state_of_health import pv_dc_combiner_module_excess_degradation
from kpi.domain.pv import pv_filter_daily_energy
from kpi.domain.solv_contract import solv_lost_period, solv_period_produced
from kpi.domain.util import filter_mask
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.arg import DeviceTypeConstant, grouper, optional, required
from kpi.op.transform.method import MethodCalc, calc_field
from kpi.registry.download.device.pv.hierarchy import DownloadDevicePvHierarchy
from kpi.registry.download.sensor.pv import DownloadSensorPv
from kpi.registry.transform.hybrid.api import date_local_5m, project_poi_limit_kw
from kpi.registry.transform.pv.clean import TransformPvClean as Clean
from kpi.registry.transform.pv.evaluate import TransformPvEvaluate as Eval


def specific_yield(energy: xr.DataArray, power_capacity: xr.DataArray) -> xr.DataArray:
    """Daily specific yield (energy per unit capacity).

    Args:
        energy: Daily energy production.
        power_capacity: Nameplate DC or AC capacity.

    Returns:
        ``energy / power_capacity``.
    """
    return energy / power_capacity


def performance_ratio_d(
    *,
    energy: xr.DataArray,
    power_capacity: xr.DataArray,
    insolation: xr.DataArray,
    reference_irradiance: float = 1000,
) -> xr.DataArray:
    """Daily performance ratio capped to [0, 1].

    Args:
        energy: Daily energy production.
        power_capacity: Nameplate DC capacity.
        insolation: Daily insolation.
        reference_irradiance: Reference POA irradiance for normalization.

    Returns:
        Performance ratio with out-of-range values masked to NaN.
    """
    yield_d = specific_yield(energy, power_capacity)
    result = yield_d / (insolation / reference_irradiance)
    return result.where(filter_mask(filter_by=result, min_value=0, max_value=1))


def project_solv_contractual_availability_d(
    *, period_kwh_produced: xr.DataArray, period_kwh_lost: xr.DataArray
) -> xr.DataArray:
    """SOLV contractual availability from produced and lost period energy.

    Args:
        period_kwh_produced: Energy produced during SOLV periods.
        period_kwh_lost: Energy lost during SOLV periods.

    Returns:
        ``produced / (produced + lost)``.
    """
    return period_kwh_produced / (period_kwh_produced + period_kwh_lost)


def project_performance_index_d(
    *, actual: xr.DataArray, expected: xr.DataArray
) -> xr.DataArray:
    """Daily performance index capped to [0, 1].

    Args:
        actual: Actual daily energy production.
        expected: Expected daily energy delivered.

    Returns:
        ``actual / expected`` for positive expected values, capped to [0, 1].
    """
    expected_positive = expected.where(expected > 0)
    ratio = actual / expected_positive
    return ratio.where(filter_mask(filter_by=ratio, min_value=0, max_value=1))


def project_curtailed_energy_kwh_d(
    *,
    power_setpoint: xr.DataArray,
    expected_energy: xr.DataArray,
    actual_energy: xr.DataArray,
    date_local_5m: xr.DataArray,
) -> xr.DataArray:
    """Daily curtailed energy during curtailment periods.

    Args:
        power_setpoint: Project power setpoint at 5-minute resolution.
        expected_energy: Expected energy at 5-minute resolution.
        actual_energy: Actual exported energy at 5-minute resolution.
        date_local_5m: Local date grouper aligned to the time dimension.

    Returns:
        Sum of non-negative ``expected - actual`` during curtailment by day.
    """
    energy_setpoint = power_setpoint / 12
    during_curtailment = actual_energy > 0.98 * energy_setpoint
    not_during_curtailment = actual_energy <= 0.98 * energy_setpoint
    curtailed_energy = (expected_energy - actual_energy).where(during_curtailment)
    curtailed_energy[curtailed_energy < 0] = 0
    curtailed_energy[not_during_curtailment] = 0
    return curtailed_energy.groupby(date_local_5m).sum()


def inverter_module_energy_kwh_d(
    *, power: xr.DataArray, date_local_5m: xr.DataArray
) -> xr.DataArray:
    """Integrate 5-minute inverter-module power to daily energy (kWh).

    Args:
        power: Inverter-module AC power at 5-minute resolution.
        date_local_5m: Local date grouper aligned to the time dimension.

    Returns:
        Daily energy as sum of 5-minute power / 12.
    """
    return power.groupby(date_local_5m).sum() / 12


def project_inverter_module_to_meter_efficiency_d(
    *,
    source: xr.DataArray,
    sink: xr.DataArray,
    power_capacity: xr.DataArray,
    min_specific_yield_h: float = 2,
) -> xr.DataArray:
    """Daily inverter-module-to-meter efficiency with low-yield days excluded.

    Args:
        source: Project inverter-module daily energy.
        sink: Project meter daily energy production.
        power_capacity: Project DC capacity for specific-yield filtering.
        min_specific_yield_h: Minimum meter specific yield (hours) to include.

    Returns:
        Efficiency ratio capped to ``[0, 1 + epsilon]``.
    """
    yield_d = specific_yield(sink, power_capacity)
    source_filtered = source.where(yield_d > min_specific_yield_h)
    efficiency = sink / source_filtered
    epsilon = 1e-06
    return efficiency.where(
        filter_mask(filter_by=efficiency, min_value=0, max_value=1 + epsilon)
    )


def combiner_field_health_d(
    *,
    combiner_current: xr.DataArray,
    combiner_power_capacity: xr.DataArray,
    time_local_5m: xr.DataArray,
    date_local_5m: xr.DataArray,
) -> xr.DataArray:
    """Daily combiner field health from noon-normalized current.

    Args:
        combiner_current: Raw combiner current at 5-minute resolution.
        combiner_power_capacity: Combiner DC capacity.
        time_local_5m: Local wall time on the 5-minute grid.
        date_local_5m: Local date grouper aligned to the time dimension.

    Returns:
        Daily mean normalized field health capped to ``[-0.1, 1.2]``.
    """
    time_dim = TimeCoord.TIME_5MIN_UTC.value
    current_ffill_1hr = combiner_current.ffill(dim=time_dim, limit=12)
    pandas_time = pd.to_datetime(time_local_5m.values)
    is_solar_noon = (pandas_time.hour == 11) & (pandas_time.minute >= 30) | (
        pandas_time.hour == 12
    ) & (pandas_time.minute <= 30)
    noon_idxs = np.flatnonzero(is_solar_noon)
    if noon_idxs.size == 0:
        is_solar_noon_array = xr.DataArray(
            is_solar_noon,
            dims=[time_dim],
            coords={time_dim: time_local_5m.coords[time_dim]},
        )
        current_at_solar_noon = current_ffill_1hr.where(is_solar_noon_array)
        first_normalization = current_at_solar_noon / combiner_power_capacity
    else:
        current_noon = current_ffill_1hr.isel({time_dim: noon_idxs})
        date_noon = date_local_5m.isel({time_dim: noon_idxs})
        first_normalization = current_noon / combiner_power_capacity
        date_local_5m = date_noon
    percentile_99 = first_normalization.quantile(
        0.99, dim=coord(DeviceTypeEnum.PV_DC_COMBINER)
    ).drop_vars("quantile")
    second_normalization = first_normalization / percentile_99
    result = second_normalization.groupby(date_local_5m).mean()
    return result.where(filter_mask(filter_by=result, min_value=-0.1, max_value=1.2))


def project_avg_combiner_field_health_d(field_health: xr.DataArray) -> xr.DataArray:
    """Project-mean combiner field health capped to [0, 1].

    Args:
        field_health: Per-combiner daily field health.

    Returns:
        Mean across combiners with out-of-range values masked to NaN.
    """
    result = field_health.mean(dim=coord(DeviceTypeEnum.PV_DC_COMBINER))
    return result.where(filter_mask(filter_by=result, min_value=0, max_value=1))


class TransformPvSummarize(FieldRegistry[MethodCalc]):
    # =======================================================
    # Project KPIs
    # =======================================================

    # PROJECT_ENERGY_PRODUCTION (6)

    project_energy_production_kwh_d = calc_field(pv_filter_daily_energy)(
        energy_unfiltered_d=required(Eval.project_energy_production_unfiltered_kwh_d),
        power_capacity=required(Clean.project_ac_power_capacity_kw),
    )

    # SMA_INVERTER_AVAILABILITY_UPTIME_PROJECT (23) deprecated

    # SPECIFIC_YIELD (33)
    specific_yield_d = calc_field(specific_yield)(
        energy=required(project_energy_production_kwh_d),
        power_capacity=required(Clean.project_dc_power_capacity_kw),
    )

    # PERFORMANCE_RATIO (34)
    performance_ratio_d = calc_field(performance_ratio_d)(
        energy=required(project_energy_production_kwh_d),
        power_capacity=required(Clean.project_dc_power_capacity_kw),
        insolation=required(Eval.project_insolation_d),
    )

    # PV_PROJECT_SOLV_PERIOD_MWH_PRODUCED (98)
    project_solv_period_produced_kwh_d = calc_field(solv_period_produced)(
        irradiance=required(Eval.project_poa_irradiance_w_m2_5m),
        power=required(Clean.pv_project_power_kw_5m),
        date_local_5m=grouper(date_local_5m),
    )

    # PV_PROJECT_SOLV_PERIOD_MWH_LOST (99)
    project_solv_period_lost_kwh_d = calc_field(solv_lost_period)(
        irradiance=required(Eval.project_poa_irradiance_w_m2_5m),
        unit_ac_power=required(Clean.inverter_ac_power_kw_5m),
        unit_power_setpoint=required(Clean.inverter_ac_power_setpoint_kw_5m),
        power=required(Clean.pv_project_power_kw_5m),
        unit_ac_capacity=required(Clean.inverter_ac_capacity_kw),
        unit_dc_capacity=required(Clean.inverter_dc_capacity_kw),
        expected_energy=required(Eval.project_expected_energy_best_kwh_5m),
        date_local_5m=grouper(date_local_5m),
    )

    # PV_PROJECT_SOLV_CONTRACTUAL_AVAILABILITY (97)
    project_solv_contractual_availability_d = calc_field(
        project_solv_contractual_availability_d
    )(
        period_kwh_produced=required(project_solv_period_produced_kwh_d),
        period_kwh_lost=required(project_solv_period_lost_kwh_d),
    )

    # PV_PROJECT_EXPECTED_ENERGY_DELIVERED (102)
    project_expected_energy_delivered_kwh_d = calc_field(resample_sum)(
        required(Eval.project_expected_energy_best_kwh_5m),
        grouper=grouper(date_local_5m),
    )

    # PV_PROJECT_PERFORMANCE_INDEX (100)
    project_performance_index_d = calc_field(project_performance_index_d)(
        actual=required(project_energy_production_kwh_d),
        expected=required(project_expected_energy_delivered_kwh_d),
    )

    # PV_PROJECT_CURTAILMENT (103)
    project_curtailed_energy_kwh_d = calc_field(project_curtailed_energy_kwh_d)(
        power_setpoint=required(Clean.project_power_setpoint_kw_5m),
        expected_energy=required(Eval.project_expected_energy_best_kwh_5m),
        actual_energy=required(Eval.project_energy_exported_to_grid_kwh_5m),
        date_local_5m=grouper(date_local_5m),
    )

    # =======================================================
    # PV Inverter KPIs
    # =======================================================

    # PV_INVERTER_MECHANICAL_AVAILABILITY (1)
    # and
    # PROJECT_PV_INVERTER_MECHANICAL_AVAILABILITY (5)
    inverter_mechanical_availability_d = calc_field(resample_mean)(
        x=required(Eval.inverter_mechanical_availability_5m),
        grouper=grouper(date_local_5m),
    )

    project_inverter_mechanical_availability_d = calc_field(daily_mean_across_devices)(
        value=required(Eval.inverter_mechanical_availability_5m),
        device_type=DeviceTypeConstant(value=DeviceTypeEnum.PV_INVERTER),
        date_local_5m=grouper(date_local_5m),
    )

    # PV_INVERTER_ENERGY_PRODUCTION (2)
    inverter_energy_production_kwh_d = calc_field(pv_filter_daily_energy)(
        energy_unfiltered_d=required(Eval.inverter_energy_production_unfiltered_kwh_d),
        power_capacity=required(Clean.inverter_dc_capacity_kw),
    )

    project_pcs_energy_production_kwh_d = calc_field(sum_across_devices)(
        required(inverter_energy_production_kwh_d),
        device_type=DeviceTypeConstant(value=DeviceTypeEnum.PV_INVERTER),
    )

    # =======================================================
    # PV Inverter Module KPIs
    # =======================================================

    # PV_INVERTER_MODULE_ENERGY_PRODUCTION (7)
    inverter_module_energy_kwh_d = calc_field(inverter_module_energy_kwh_d)(
        power=required(Clean.inverter_module_ac_power_kw_5m),
        date_local_5m=grouper(date_local_5m),
    )

    project_inverter_module_energy_kwh_d = calc_field(sum_across_devices)(
        required(inverter_module_energy_kwh_d),
        device_type=DeviceTypeConstant(value=DeviceTypeEnum.PV_INVERTER_MODULE),
    )

    project_inverter_module_to_meter_efficiency_d = calc_field(
        project_inverter_module_to_meter_efficiency_d
    )(
        source=required(project_inverter_module_energy_kwh_d),
        sink=required(project_energy_production_kwh_d),
        power_capacity=required(Clean.project_dc_power_capacity_kw),
    )

    # =======================================================
    # Tracker Row KPIs
    # =======================================================

    # TRACKER_AVAILABILITY_BY_ROW (4)

    tracker_row_availability_d = calc_field(resample_mean)(
        x=required(Eval.tracker_row_is_available_5m),
        grouper=grouper(date_local_5m),
    )

    project_tracker_row_availability_d = calc_field(daily_mean_across_devices)(
        value=required(Eval.tracker_row_is_available_5m),
        device_type=DeviceTypeConstant(value=DeviceTypeEnum.TRACKER_ROW),
        date_local_5m=grouper(date_local_5m),
    )

    # TRACKER_POSITION_DEVIATING_FROM_SETPOINT_BY_ROW (21)

    tracker_row_deviation_from_setpoint_deg_d = calc_field(resample_mean)(
        x=required(Eval.tracker_row_deviation_from_setpoint_deg_5m),
        grouper=grouper(date_local_5m),
    )

    project_tracker_row_deviation_from_setpoint_deg_d = calc_field(
        daily_mean_across_devices
    )(
        value=required(Eval.tracker_row_deviation_from_setpoint_deg_5m),
        device_type=DeviceTypeConstant(value=DeviceTypeEnum.TRACKER_ROW),
        date_local_5m=grouper(date_local_5m),
    )

    # TRACKER_SETPOINT_DEVIATING_FROM_MEDIAN_BY_ROW (22)
    tracker_row_setpoint_deviating_from_median_deg_d = calc_field(resample_mean)(
        x=required(Eval.tracker_row_setpoint_deviation_from_median_deg_5m),
        grouper=grouper(date_local_5m),
    )

    project_tracker_row_setpoint_deviating_from_median_deg_d = calc_field(
        daily_mean_across_devices
    )(
        value=required(Eval.tracker_row_setpoint_deviation_from_median_deg_5m),
        device_type=DeviceTypeConstant(value=DeviceTypeEnum.TRACKER_ROW),
        date_local_5m=grouper(date_local_5m),
    )

    # =======================================================
    # PV Block KPIs
    # =======================================================

    # TRACKER_AVAILABILITY_BY_BLOCK (3)
    block_tracker_row_availability_d = calc_field(daily_mean_across_grouped_devices)(
        value=required(Eval.tracker_row_is_available_5m),
        device_mapping=required(DownloadDevicePvHierarchy.tracker_row_to_block),
        device_type=DeviceTypeConstant(value=DeviceTypeEnum.PV_BLOCK),
        date_local_5m=grouper(date_local_5m),
    )

    # see above for project level availability

    # TRACKER_POSITION_DEVIATING_FROM_SETPOINT_BY_BLOCK (18)
    block_tracker_row_deviation_from_setpoint_deg_d = calc_field(
        daily_mean_across_grouped_devices
    )(
        value=required(Eval.tracker_row_deviation_from_setpoint_deg_5m),
        device_mapping=required(DownloadDevicePvHierarchy.tracker_row_to_block),
        device_type=DeviceTypeConstant(value=DeviceTypeEnum.PV_BLOCK),
        date_local_5m=grouper(date_local_5m),
    )

    # see above for project level deviation from setpoint

    # TRACKER_SETPOINT_DEVIATING_FROM_MEDIAN_BY_BLOCK (19)
    block_tracker_row_setpoint_deviating_from_median_deg_d = calc_field(
        daily_mean_across_grouped_devices
    )(
        value=required(Eval.tracker_row_setpoint_deviation_from_median_deg_5m),
        device_mapping=required(DownloadDevicePvHierarchy.tracker_row_to_block),
        device_type=DeviceTypeConstant(value=DeviceTypeEnum.PV_BLOCK),
        date_local_5m=grouper(date_local_5m),
    )

    # see above for project level setpoint deviating from median

    # =======================================================
    # PV DC Combiner KPIs
    # =======================================================

    # PV_DC_COMBINER_FIELD_HEALTH (8)
    combiner_field_health_d = calc_field(combiner_field_health_d)(
        combiner_current=required(DownloadSensorPv.combiner_current_raw_amps_5m),
        combiner_power_capacity=required(Clean.combiner_dc_capacity_kw),
        time_local_5m=required(Eval.time_local_5m),
        date_local_5m=grouper(date_local_5m),
    )

    project_avg_combiner_field_health_d = calc_field(
        project_avg_combiner_field_health_d
    )(field_health=required(combiner_field_health_d))

    # MODULE_STATE_OF_HEALTH_BY_COMBINER (17)
    combiner_module_excess_degradation_d = calc_field(
        pv_dc_combiner_module_excess_degradation
    )(
        met_station_irradiance_poa_w_m2_5m=required(Clean.met_poa_irradiance_w_m2_5m),
        project_theoretical_poa_irradiance_w_m2_5m=required(
            Eval.project_theoretical_poa_irradiance_w_m2_5m
        ),
        project_meter_power_kw_5m=required(Clean.pv_project_power_kw_5m),
        project_poi_limit_kw=required(project_poi_limit_kw),
        pv_inverter_ac_power_kw_5m=required(Clean.inverter_ac_power_kw_5m),
        pv_inverter_ac_power_capacity_kw=required(Clean.inverter_ac_capacity_kw),
        pv_inverter_reactive_power_kvar_5m=required(
            Clean.inverter_reactive_power_kvar_5m
        ),
        pv_inverter_module_voltage_v_5m=required(Clean.inverter_module_voltage_v_5m),
        pv_inverter_module_power_kw_5m=required(Clean.inverter_module_ac_power_kw_5m),
        pv_inverter_module_power_capacity_kw=required(
            Clean.inverter_module_ac_capacity_kw
        ),
        block_tracker_row_deviation_from_setpoint_deg_d=required(
            block_tracker_row_deviation_from_setpoint_deg_d
        ),
        block_tracker_row_setpoint_deviation_from_median_deg_d=required(
            block_tracker_row_setpoint_deviating_from_median_deg_d
        ),
        pv_dc_combiner_field_health_d=required(combiner_field_health_d),
        pv_dc_combiner_current_amps_5m=required(
            DownloadSensorPv.combiner_current_raw_amps_5m
        ),
        pv_dc_combiner_expected_energy_kwh_5m=required(
            Eval.combiner_expected_energy_best_kwh_5m
        ),
        date_local_5m=grouper(date_local_5m),
        combiner_to_inverter=required(DownloadDevicePvHierarchy.combiner_to_inverter),
        combiner_to_block=required(DownloadDevicePvHierarchy.combiner_to_block),
        inverter_module_to_inverter=required(
            DownloadDevicePvHierarchy.inverter_module_to_inverter
        ),
        pv_inverter_ac_power_setpoint_kw_5m=optional(
            Clean.inverter_ac_power_setpoint_kw_5m
        ),
        pv_inverter_voltage_v_5m=optional(Clean.inverter_voltage_v_5m),
    )

    project_combiner_module_excess_degradation_d = calc_field(mean_across_devices)(
        required(combiner_module_excess_degradation_d),
        device_type=DeviceTypeConstant(value=DeviceTypeEnum.PV_DC_COMBINER),
    )

    # PV_DC_COMBINER_MECHANICAL_AVAILABILITY (101)
    combiner_mechanical_availability_d = calc_field(resample_mean)(
        x=required(Eval.combiner_mechanical_availability_5m),
        grouper=grouper(date_local_5m),
    )

    project_combiner_mechanical_availability_d = calc_field(daily_mean_across_devices)(
        value=required(Eval.combiner_mechanical_availability_5m),
        device_type=DeviceTypeConstant(value=DeviceTypeEnum.PV_DC_COMBINER),
        date_local_5m=grouper(date_local_5m),
    )
