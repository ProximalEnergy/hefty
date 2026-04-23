import numpy as np
import pandas as pd
import xarray as xr
from core.enumerations import DeviceType
from kpi.base.enumeration import TimeCoords
from kpi.base.protocol import CalcProtocol
from kpi.base.util import coord
from kpi.domain.module_state_of_health import pv_dc_combiner_module_excess_degradation
from kpi.domain.solv_contract import solv_lost_period, solv_period_produced
from kpi.domain.util import (
    daily_mean_across_devices,
    daily_mean_across_grouped_devices,
    date_local,
    diff,
    filter_mask,
)
from kpi.op.field import MakeField
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.method import method_calc, optional, required
from kpi.registry.download.device.pv.hierarchy import DownloadDevicePvHierarchy
from kpi.registry.download.sensor.pv import DownloadSensorPv
from kpi.registry.transform.hybrid.api import date_local_5m, project_poi_limit_kw
from kpi.registry.transform.pv.clean import TransformPvClean as Clean
from kpi.registry.transform.pv.evaluate import TransformPvEvaluate as Eval

field = MakeField[CalcProtocol].infer_doc


class TransformPvSummarize(FieldRegistry[CalcProtocol]):
    # =======================================================
    # Project KPIs
    # =======================================================

    # PROJECT_ENERGY_PRODUCTION (6)
    @method_calc
    def project_energy_production_kwh_d(
        energy_total: xr.DataArray = required(
            Clean.project_total_delivered_energy_filled_kwh_5m
        ),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        energy_total_d = energy_total.groupby(date_local(date_local_5m)).first()
        return diff(energy_total_d, time_dim=TimeCoords.DATE_LOCAL)

    # SMA_INVERTER_AVAILABILITY_UPTIME_PROJECT (23) deprecated

    # SPECIFIC_YIELD (33)
    @method_calc
    def specific_yield_d(
        energy: xr.DataArray = required(project_energy_production_kwh_d),
        power_capacity: xr.DataArray = required(Clean.project_dc_capacity_kw),
    ) -> xr.DataArray:
        return energy / power_capacity

    # PERFORMANCE_RATIO (34)
    @method_calc
    def performance_ratio_d(
        energy: xr.DataArray = required(project_energy_production_kwh_d),
        power_capacity: xr.DataArray = required(Clean.project_dc_capacity_kw),
        insolation: xr.DataArray = required(Eval.project_insolation_d),
    ) -> xr.DataArray:
        reference_irradiance = 1000
        specific_yield = energy / power_capacity
        result = specific_yield / (insolation / reference_irradiance)
        return result.where(filter_mask(filter_by=result, min_value=0, max_value=1))

    # PV_PROJECT_SOLV_PERIOD_MWH_PRODUCED (98)
    @method_calc
    def project_solv_period_produced_kwh_d(
        irradiance: xr.DataArray = required(Eval.project_poa_irradiance_w_m2_5m),
        power: xr.DataArray = required(Clean.pv_project_power_kw_5m),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        return solv_period_produced(
            irradiance=irradiance,
            power=power,
            date_local_5m=date_local_5m,
        )

    # PV_PROJECT_SOLV_PERIOD_MWH_LOST (99)
    @method_calc
    def project_solv_period_lost_kwh_d(
        irradiance: xr.DataArray = required(Eval.project_poa_irradiance_w_m2_5m),
        unit_power: xr.DataArray = required(Clean.inverter_ac_power_kw_5m),
        unit_power_setpoint: xr.DataArray = required(
            Clean.inverter_ac_power_setpoint_kw_5m
        ),
        project_power: xr.DataArray = required(Clean.pv_project_power_kw_5m),
        unit_ac_capacity: xr.DataArray = required(Clean.inverter_ac_capacity_kw),
        unit_dc_capacity: xr.DataArray = required(Clean.inverter_dc_capacity_kw),
        project_expected_energy: xr.DataArray = required(
            Eval.project_expected_energy_best_kw_5m
        ),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        return solv_lost_period(
            irradiance=irradiance,
            unit_ac_power=unit_power,
            unit_power_setpoint=unit_power_setpoint,
            power=project_power,
            unit_ac_capacity=unit_ac_capacity,
            unit_dc_capacity=unit_dc_capacity,
            expected_energy=project_expected_energy,
            date_local_5m=date_local_5m,
        )

    # PV_PROJECT_SOLV_CONTRACTUAL_AVAILABILITY (97)
    @method_calc
    def project_solv_contractual_availability_d(
        period_kwh_produced: xr.DataArray = required(
            project_solv_period_produced_kwh_d
        ),
        period_kwh_lost: xr.DataArray = required(project_solv_period_lost_kwh_d),
    ) -> xr.DataArray:
        return period_kwh_produced / (period_kwh_produced + period_kwh_lost)

    # PV_PROJECT_EXPECTED_ENERGY_DELIVERED (102)
    @method_calc
    def project_expected_energy_delivered_kwh_d(
        expected_energy: xr.DataArray = required(
            Eval.project_expected_energy_best_kw_5m
        ),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        return expected_energy.groupby(date_local(date_local_5m)).sum()

    # PV_PROJECT_PERFORMANCE_INDEX (100)
    @method_calc
    def project_performance_index_d(
        actual: xr.DataArray = required(project_energy_production_kwh_d),
        expected: xr.DataArray = required(project_expected_energy_delivered_kwh_d),
    ) -> xr.DataArray:
        expected = expected.where(expected > 0)
        ratio = actual / expected
        return ratio.where(filter_mask(filter_by=ratio, min_value=0, max_value=1))

    # PV_PROJECT_CURTAILMENT (103)
    @method_calc
    def project_curtailed_energy_kwh_d(
        power_setpoint: xr.DataArray = required(Clean.project_power_setpoint_kw_5m),
        expected_energy: xr.DataArray = required(
            Eval.project_expected_energy_best_kw_5m
        ),
        actual_energy: xr.DataArray = required(Eval.project_delivered_energy_kwh_5m),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        energy_setpoint = power_setpoint / 12

        during_curtailment = actual_energy > 0.98 * energy_setpoint
        not_during_curtailment = actual_energy <= 0.98 * energy_setpoint
        # if a time stamp is missing actual energy or energy setpoint, it's false
        # for both of these conditions.
        curtailed_energy = (expected_energy - actual_energy).where(during_curtailment)
        curtailed_energy[curtailed_energy < 0] = 0
        curtailed_energy[not_during_curtailment] = 0

        return curtailed_energy.groupby(date_local(date_local_5m)).sum()

    # =======================================================
    # PV Inverter KPIs
    # =======================================================

    # PV_INVERTER_MECHANICAL_AVAILABILITY (1)
    # and
    # PROJECT_PV_INVERTER_MECHANICAL_AVAILABILITY (5)
    @method_calc
    def inverter_mechanical_availability_d(
        is_available: xr.DataArray = required(Eval.inverter_mechanical_availability_5m),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        return is_available.groupby(date_local(date_local_5m)).mean()

    @method_calc
    def project_inverter_mechanical_availability_d(
        is_available: xr.DataArray = required(Eval.inverter_mechanical_availability_5m),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=is_available,
            device_type=DeviceType.PV_INVERTER,
            date_local_5m=date_local_5m,
        )

    # PV_INVERTER_ENERGY_PRODUCTION (2)
    @method_calc
    def inverter_energy_production_kwh_d(
        energy: xr.DataArray = required(
            Clean.inverter_total_energy_production_filled_kwh_5m
        ),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        energy_total_d = energy.groupby(date_local(date_local_5m)).first()
        return diff(energy_total_d, time_dim=TimeCoords.DATE_LOCAL)

    @method_calc
    def project_pcs_energy_production_kwh_d(
        energy: xr.DataArray = required(inverter_energy_production_kwh_d),
    ) -> xr.DataArray:
        return energy.sum(dim=coord(DeviceType.PV_INVERTER))

    # =======================================================
    # PV Inverter Module KPIs
    # =======================================================

    # PV_INVERTER_MODULE_ENERGY_PRODUCTION (7)
    @method_calc
    def inverter_module_energy_kwh_d(
        power: xr.DataArray = required(Clean.inverter_module_ac_power_kw_5m),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        return power.groupby(date_local(date_local_5m)).sum() / 12

    @method_calc
    def project_inverter_module_energy_kwh_d(
        energy: xr.DataArray = required(inverter_module_energy_kwh_d),
    ) -> xr.DataArray:
        return energy.sum(dim=coord(DeviceType.PV_INVERTER_MODULE))

    @method_calc
    def project_inverter_module_to_meter_efficiency_d(
        source: xr.DataArray = required(project_inverter_module_energy_kwh_d),
        sink: xr.DataArray = required(project_energy_production_kwh_d),
        power_capacity: xr.DataArray = required(Clean.project_dc_capacity_kw),
    ) -> xr.DataArray:
        """
        Project Inverter Module to Meter Efficiency per Day
        Used to calculate `PV_PROJECT_INVERTER_MODULE_TO_METER_EFFICIENCY` (122).
        Energy produced at the meter divided by the total energy
        produced at the inverter module level. Days where the specific
        yield was less than 2 hours are excluded.
        """
        specific_yield = sink / power_capacity
        source_filtered = source.where(specific_yield > 2)
        efficiency = sink / source_filtered
        epsilon = 1e-6
        return efficiency.where(
            filter_mask(filter_by=efficiency, min_value=0, max_value=1 + epsilon)
        )

    # =======================================================
    # Tracker Row KPIs
    # =======================================================

    # TRACKER_AVAILABILITY_BY_ROW (4)

    @method_calc
    def tracker_row_availability_d(
        is_available: xr.DataArray = required(Eval.tracker_row_is_available_5m),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        return is_available.groupby(date_local(date_local_5m)).mean()

    @method_calc
    def project_tracker_row_availability_d(
        is_available: xr.DataArray = required(Eval.tracker_row_is_available_5m),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=is_available,
            device_type=DeviceType.TRACKER_ROW,
            date_local_5m=date_local_5m,
        )

    # TRACKER_POSITION_DEVIATING_FROM_SETPOINT_BY_ROW (21)

    @method_calc
    def tracker_row_deviation_from_setpoint_deg_d(
        position: xr.DataArray = required(Clean.tracker_row_position_deg_5m),
        setpoint: xr.DataArray = required(Clean.tracker_row_setpoint_deg_5m),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        return abs(position - setpoint).groupby(date_local(date_local_5m)).mean()

    @method_calc
    def project_tracker_row_deviation_from_setpoint_deg_d(
        position: xr.DataArray = required(Clean.tracker_row_position_deg_5m),
        setpoint: xr.DataArray = required(Clean.tracker_row_setpoint_deg_5m),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=abs(position - setpoint),
            device_type=DeviceType.TRACKER_ROW,
            date_local_5m=date_local_5m,
        )

    # TRACKER_SETPOINT_DEVIATING_FROM_MEDIAN_BY_ROW (22)
    @method_calc
    def tracker_row_setpoint_deviating_from_median_deg_d(
        setpoint: xr.DataArray = required(Clean.tracker_row_setpoint_deg_5m),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        median_setpoint = setpoint.median(dim=coord(DeviceType.TRACKER_ROW))
        return abs(setpoint - median_setpoint).groupby(date_local(date_local_5m)).mean()

    @method_calc
    def project_tracker_row_setpoint_deviating_from_median_deg_d(
        setpoint: xr.DataArray = required(Clean.tracker_row_setpoint_deg_5m),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        median_setpoint = setpoint.median(dim=coord(DeviceType.TRACKER_ROW))
        return daily_mean_across_devices(
            value=abs(setpoint - median_setpoint),
            device_type=DeviceType.TRACKER_ROW,
            date_local_5m=date_local_5m,
        )

    # =======================================================
    # PV Block KPIs
    # =======================================================

    # TRACKER_AVAILABILITY_BY_BLOCK (3)
    @method_calc
    def block_tracker_row_availability_d(
        is_available: xr.DataArray = required(Eval.tracker_row_is_available_5m),
        device_mapping: xr.DataArray = required(
            DownloadDevicePvHierarchy.tracker_row_to_block
        ),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        return daily_mean_across_grouped_devices(
            value=is_available,
            device_mapping=device_mapping,
            device_type=DeviceType.PV_BLOCK,
            date_local_5m=date_local_5m,
        )

    # see above for project level availability

    # TRACKER_POSITION_DEVIATING_FROM_SETPOINT_BY_BLOCK (18)
    @method_calc
    def block_tracker_row_deviation_from_setpoint_deg_d(
        position: xr.DataArray = required(Clean.tracker_row_position_deg_5m),
        setpoint: xr.DataArray = required(Clean.tracker_row_setpoint_deg_5m),
        device_mapping: xr.DataArray = required(
            DownloadDevicePvHierarchy.tracker_row_to_block
        ),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        return daily_mean_across_grouped_devices(
            value=abs(position - setpoint),
            device_mapping=device_mapping,
            device_type=DeviceType.PV_BLOCK,
            date_local_5m=date_local_5m,
        )

    # see above for project level deviation from setpoint

    # TRACKER_SETPOINT_DEVIATING_FROM_MEDIAN_BY_BLOCK (19)
    @method_calc
    def block_tracker_row_setpoint_deviating_from_median_deg_d(
        setpoint: xr.DataArray = required(Clean.tracker_row_setpoint_deg_5m),
        device_mapping: xr.DataArray = required(
            DownloadDevicePvHierarchy.tracker_row_to_block
        ),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        return daily_mean_across_grouped_devices(
            value=abs(setpoint - setpoint.median(dim=coord(DeviceType.TRACKER_ROW))),
            device_mapping=device_mapping,
            device_type=DeviceType.PV_BLOCK,
            date_local_5m=date_local_5m,
        )

    # see above for project level setpoint deviating from median

    # =======================================================
    # PV DC Combiner KPIs
    # =======================================================

    # PV_DC_COMBINER_FIELD_HEALTH (8)
    @method_calc
    def combiner_field_health_d(
        combiner_current: xr.DataArray = required(
            DownloadSensorPv.combiner_current_raw_amps_5m
        ),
        combiner_power_capacity: xr.DataArray = required(Clean.combiner_dc_capacity_kw),
        time_local_5m: xr.DataArray = required(Eval.time_local_5m),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        time_dim = TimeCoords.TIME_5MIN_UTC.value
        current_ffill_1hr = combiner_current.ffill(dim=time_dim, limit=12)
        pandas_time = pd.to_datetime(time_local_5m.values)
        is_solar_noon = ((pandas_time.hour == 11) & (pandas_time.minute >= 30)) | (
            (pandas_time.hour == 12) & (pandas_time.minute <= 30)
        )
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
            0.99, dim=coord(DeviceType.PV_DC_COMBINER)
        ).drop_vars("quantile")
        second_normalization = first_normalization / percentile_99
        result = second_normalization.groupby(date_local(date_local_5m)).mean()
        return result.where(
            filter_mask(filter_by=result, min_value=-0.1, max_value=1.2)
        )

    @method_calc
    def project_avg_combiner_field_health_d(
        field_health: xr.DataArray = required(combiner_field_health_d),
    ) -> xr.DataArray:
        result = field_health.mean(dim=coord(DeviceType.PV_DC_COMBINER))
        return result.where(filter_mask(filter_by=result, min_value=0, max_value=1))

    # MODULE_STATE_OF_HEALTH_BY_COMBINER (17)
    @method_calc
    def combiner_module_excess_degradation_d(
        met_irradiance: xr.DataArray = required(Clean.met_poa_irradiance_w_m2_5m),
        theoretical_irradiance: xr.DataArray = required(
            Eval.project_theoretical_poa_irradiance_w_m2_5m
        ),
        power: xr.DataArray = required(Clean.pv_project_power_kw_5m),
        poi_limit: xr.DataArray = required(project_poi_limit_kw),
        inverter_power: xr.DataArray = required(Clean.inverter_ac_power_kw_5m),
        inverter_capacity: xr.DataArray = required(Clean.inverter_ac_capacity_kw),
        inverter_reactive_power: xr.DataArray = required(
            Clean.inverter_reactive_power_kvar_5m
        ),
        inverter_module_voltage: xr.DataArray = required(
            Clean.inverter_module_voltage_v_5m
        ),
        inverter_module_power: xr.DataArray = required(
            Clean.inverter_module_ac_power_kw_5m
        ),
        inverter_module_capacity: xr.DataArray = required(
            Clean.inverter_module_ac_capacity_kw
        ),
        block_tracker_row_deviation_from_setpoint: xr.DataArray = required(
            block_tracker_row_deviation_from_setpoint_deg_d
        ),
        block_tracker_row_setpoint_deviation_from_median: xr.DataArray = required(
            block_tracker_row_setpoint_deviating_from_median_deg_d
        ),
        combiner_field_health: xr.DataArray = required(combiner_field_health_d),
        combiner_current: xr.DataArray = required(
            DownloadSensorPv.combiner_current_raw_amps_5m
        ),
        combiner_expected_energy: xr.DataArray = required(
            Eval.combiner_expected_energy_best_kwh_5m
        ),
        date_local_5m: xr.DataArray = required(date_local_5m),
        combiner_to_inverter: xr.DataArray = required(
            DownloadDevicePvHierarchy.combiner_to_inverter
        ),
        combiner_to_block: xr.DataArray = required(
            DownloadDevicePvHierarchy.combiner_to_block
        ),
        inverter_module_to_inverter: xr.DataArray = required(
            DownloadDevicePvHierarchy.inverter_module_to_inverter
        ),
        inverter_power_setpoint: xr.DataArray | None = optional(
            Clean.inverter_ac_power_setpoint_kw_5m
        ),
        inverter_voltage: xr.DataArray | None = optional(Clean.inverter_voltage_v_5m),
    ) -> xr.DataArray:
        return pv_dc_combiner_module_excess_degradation(
            met_station_irradiance_poa_w_m2_5m=met_irradiance,
            project_theoretical_poa_irradiance_w_m2_5m=theoretical_irradiance,
            project_meter_power_kw_5m=power,
            project_poi_limit_kw=poi_limit,
            pv_inverter_ac_power_kw_5m=inverter_power,
            pv_inverter_ac_power_capacity_kw=inverter_capacity,
            pv_inverter_reactive_power_kvar_5m=inverter_reactive_power,
            pv_inverter_module_voltage_v_5m=inverter_module_voltage,
            pv_inverter_module_power_kw_5m=inverter_module_power,
            pv_inverter_module_power_capacity_kw=inverter_module_capacity,
            block_tracker_row_deviation_from_setpoint_deg_d=block_tracker_row_deviation_from_setpoint,
            block_tracker_row_setpoint_deviation_from_median_deg_d=block_tracker_row_setpoint_deviation_from_median,
            pv_dc_combiner_field_health_d=combiner_field_health,
            pv_dc_combiner_current_amps_5m=combiner_current,
            pv_dc_combiner_expected_energy_kwh_5m=combiner_expected_energy,
            date_local_5m=date_local_5m,
            combiner_to_inverter=combiner_to_inverter,
            combiner_to_block=combiner_to_block,
            inverter_module_to_inverter=inverter_module_to_inverter,
            pv_inverter_ac_power_setpoint_kw_5m=inverter_power_setpoint,
            pv_inverter_voltage_v_5m=inverter_voltage,
        )

    @method_calc
    def project_combiner_module_excess_degradation_d(
        module_excess_degradation: xr.DataArray = required(
            combiner_module_excess_degradation_d
        ),
    ) -> xr.DataArray:
        return module_excess_degradation.mean(dim=coord(DeviceType.PV_DC_COMBINER))

    # PV_DC_COMBINER_MECHANICAL_AVAILABILITY (101)
    @method_calc
    def combiner_mechanical_availability_d(
        is_available: xr.DataArray = required(Eval.combiner_mechanical_availability_5m),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        return is_available.groupby(date_local(date_local_5m)).mean()

    @method_calc
    def project_combiner_mechanical_availability_d(
        is_available: xr.DataArray = required(Eval.combiner_mechanical_availability_5m),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=is_available,
            device_type=DeviceType.PV_DC_COMBINER,
            date_local_5m=date_local_5m,
        )
