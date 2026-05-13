import numpy as np
import xarray as xr
from core.enumerations import DeviceTypeEnum
from kpi.base.enumeration import TimeCoord
from kpi.base.protocol import CalcProtocol
from kpi.domain.agg.across_devices import mean_across_devices, sum_across_devices
from kpi.domain.agg.resample import resample_diff, resample_sum
from kpi.domain.bess import (
    c_rate,
    c_rate_while_charging,
    c_rate_while_discharging,
    is_charging,
    is_discharging,
    is_idling,
    resting_soc,
)
from kpi.domain.general import filter_energy_5m
from kpi.domain.util import (
    available_from_event,
    diff,
    fill_accumulator,
    time_grouper,
    where,
)
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.arg import Constant, Grouper, Required, TimeCoordArg, TimeZone
from kpi.op.transform.method import calc_field, method_calc
from kpi.registry.download.sensor.bess import DownloadSensorBess
from kpi.registry.transform.bess.clean.api import TransformBessClean as Clean


class TransformBessEvaluateKpi(FieldRegistry[CalcProtocol]):
    date_local_5m = calc_field(time_grouper)(
        from_time=TimeCoordArg(TimeCoord.TIME_5MIN_UTC),
        from_time_coord=Constant(TimeCoord.TIME_5MIN_UTC),
        to_time_coord=Constant(TimeCoord.DATE_LOCAL),
        time_zone=TimeZone(),
    )

    hour_utc_5m = calc_field(time_grouper)(
        from_time=TimeCoordArg(TimeCoord.TIME_5MIN_UTC),
        from_time_coord=Constant(TimeCoord.TIME_5MIN_UTC),
        to_time_coord=Constant(TimeCoord.HOUR_UTC),
    )

    # =======================================================
    # Backfill and forward fill accumulators to remove nans
    # =======================================================

    # project level

    project_total_energy_charged_filled_kwh_5m = calc_field(fill_accumulator)(
        Required(DownloadSensorBess.project_total_energy_charged_raw_kwh_5m),
    )

    project_total_energy_discharged_filled_kwh_5m = calc_field(fill_accumulator)(
        Required(DownloadSensorBess.project_total_energy_discharged_raw_kwh_5m),
    )

    project_total_aux_energy_filled_kwh_5m = calc_field(fill_accumulator)(
        Required(DownloadSensorBess.project_total_aux_energy_raw_kwh_5m),
    )

    # mv circuit level

    circuit_total_energy_charged_filled_kwh_5m = calc_field(fill_accumulator)(
        Required(DownloadSensorBess.circuit_total_energy_charged_raw_kwh_5m),
    )

    circuit_total_energy_discharged_filled_kwh_5m = calc_field(fill_accumulator)(
        Required(DownloadSensorBess.circuit_total_energy_discharged_raw_kwh_5m),
    )

    # pcs level

    pcs_total_energy_charged_filled_kwh_5m = calc_field(fill_accumulator)(
        Required(DownloadSensorBess.pcs_total_energy_charged_raw_kwh_5m),
    )

    pcs_total_energy_discharged_filled_kwh_5m = calc_field(fill_accumulator)(
        Required(DownloadSensorBess.pcs_total_energy_discharged_raw_kwh_5m),
    )

    # pcs module level

    pcs_module_total_energy_charged_filled_kwh_5m = calc_field(fill_accumulator)(
        Required(DownloadSensorBess.pcs_module_total_energy_charged_raw_kwh_5m),
    )

    pcs_module_total_energy_discharged_filled_kwh_5m = calc_field(fill_accumulator)(
        Required(DownloadSensorBess.pcs_module_total_energy_discharged_raw_kwh_5m),
    )

    # string level

    string_total_energy_charged_filled_kwh_5m = calc_field(fill_accumulator)(
        Required(DownloadSensorBess.string_total_energy_charged_raw_kwh_5m),
    )

    string_total_energy_discharged_filled_kwh_5m = calc_field(fill_accumulator)(
        Required(DownloadSensorBess.string_total_energy_discharged_raw_kwh_5m),
    )

    # =======================================================
    # Estimate 5-minute energy
    # =======================================================

    # Project level

    project_energy_charged_unfiltered_kwh_5m = calc_field(diff)(
        Required(project_total_energy_charged_filled_kwh_5m),
    )

    project_energy_charged_kwh_5m = calc_field(filter_energy_5m)(
        energy_unfiltered_5m=Required(project_energy_charged_unfiltered_kwh_5m),
        power_capacity=Required(Clean.project_power_capacity_kw),
    )

    project_energy_discharged_unfiltered_kwh_5m = calc_field(diff)(
        Required(project_total_energy_discharged_filled_kwh_5m),
    )

    project_energy_discharged_kwh_5m = calc_field(filter_energy_5m)(
        energy_unfiltered_5m=Required(project_energy_discharged_unfiltered_kwh_5m),
        power_capacity=Required(Clean.project_power_capacity_kw),
    )

    # PCS level

    pcs_energy_charged_unfiltered_kwh_5m = calc_field(diff)(
        Required(pcs_total_energy_charged_filled_kwh_5m),
    )

    pcs_energy_charged_kwh_5m = calc_field(filter_energy_5m)(
        energy_unfiltered_5m=Required(pcs_energy_charged_unfiltered_kwh_5m),
        power_capacity=Required(Clean.pcs_power_capacity_kw),
    )

    project_pcs_energy_charged_kwh_5m = calc_field(sum_across_devices)(
        Required(pcs_energy_charged_kwh_5m),
        device_type=Constant(DeviceTypeEnum.BESS_PCS),
    )

    pcs_energy_discharged_unfiltered_kwh_5m = calc_field(diff)(
        Required(pcs_total_energy_discharged_filled_kwh_5m),
    )

    pcs_energy_discharged_kwh_5m = calc_field(filter_energy_5m)(
        energy_unfiltered_5m=Required(pcs_energy_discharged_unfiltered_kwh_5m),
        power_capacity=Required(Clean.pcs_power_capacity_kw),
    )

    project_pcs_energy_discharged_kwh_5m = calc_field(sum_across_devices)(
        Required(pcs_energy_discharged_kwh_5m),
        device_type=Constant(DeviceTypeEnum.BESS_PCS),
    )

    # =======================================================
    # Estimate daily energy
    # =======================================================

    # project

    project_energy_charged_unfiltered_kwh_d = calc_field(resample_diff)(
        Required(project_total_energy_charged_filled_kwh_5m),
        grouper=Grouper(date_local_5m),
    )

    project_energy_discharged_unfiltered_kwh_d = calc_field(resample_diff)(
        Required(project_total_energy_discharged_filled_kwh_5m),
        grouper=Grouper(date_local_5m),
    )

    # aux

    project_aux_energy_unfiltered_kwh_d = calc_field(resample_diff)(
        Required(project_total_aux_energy_filled_kwh_5m),
        grouper=Grouper(date_local_5m),
    )

    # circuit

    circuit_energy_charged_unfiltered_kwh_d = calc_field(resample_diff)(
        Required(circuit_total_energy_charged_filled_kwh_5m),
        grouper=Grouper(date_local_5m),
    )

    circuit_energy_discharged_unfiltered_kwh_d = calc_field(resample_diff)(
        Required(circuit_total_energy_discharged_filled_kwh_5m),
        grouper=Grouper(date_local_5m),
    )

    # pcs

    pcs_energy_charged_dc_unfiltered_kwh_d = calc_field(resample_diff)(
        Required(pcs_total_energy_charged_filled_kwh_5m),
        grouper=Grouper(date_local_5m),
    )

    pcs_energy_discharged_dc_unfiltered_kwh_d = calc_field(resample_diff)(
        Required(pcs_total_energy_discharged_filled_kwh_5m),
        grouper=Grouper(date_local_5m),
    )

    # pcs module

    pcs_module_energy_charged_unfiltered_kwh_d = calc_field(resample_diff)(
        Required(pcs_module_total_energy_charged_filled_kwh_5m),
        grouper=Grouper(date_local_5m),
    )

    pcs_module_energy_discharged_unfiltered_kwh_d = calc_field(resample_diff)(
        Required(pcs_module_total_energy_discharged_filled_kwh_5m),
        grouper=Grouper(date_local_5m),
    )

    # string

    string_energy_charged_unfiltered_kwh_d = calc_field(resample_diff)(
        Required(string_total_energy_charged_filled_kwh_5m),
        grouper=Grouper(date_local_5m),
    )

    string_energy_discharged_unfiltered_kwh_d = calc_field(resample_diff)(
        Required(string_total_energy_discharged_filled_kwh_5m),
        grouper=Grouper(date_local_5m),
    )

    # =======================================================
    # C-Rate
    # =======================================================

    # project level

    project_c_rate_5m = calc_field(c_rate)(
        power=Required(Clean.project_power_kw_5m),
        energy_capacity=Required(Clean.project_energy_capacity_kwh),
    )

    project_c_rate_while_charging_5m = calc_field(c_rate_while_charging)(
        c_rate=Required(project_c_rate_5m),
    )

    project_c_rate_while_discharging_5m = calc_field(c_rate_while_discharging)(
        c_rate=Required(project_c_rate_5m),
    )

    # pcs level

    pcs_c_rate_5m = calc_field(c_rate)(
        power=Required(Clean.pcs_power_kw_5m),
        energy_capacity=Required(Clean.pcs_energy_capacity_kwh),
    )

    pcs_c_rate_while_charging_5m = calc_field(c_rate_while_charging)(
        c_rate=Required(pcs_c_rate_5m),
    )

    pcs_c_rate_while_discharging_5m = calc_field(c_rate_while_discharging)(
        c_rate=Required(pcs_c_rate_5m),
    )

    # string level

    string_c_rate_5m = calc_field(c_rate)(
        power=Required(Clean.string_power_kw_5m),
        energy_capacity=Required(Clean.string_energy_capacity_kwh),
    )

    string_c_rate_while_charging_5m = calc_field(c_rate_while_charging)(
        c_rate=Required(string_c_rate_5m),
    )

    string_c_rate_while_discharging_5m = calc_field(c_rate_while_discharging)(
        c_rate=Required(string_c_rate_5m),
    )

    # =======================================================
    # Resting SOC
    # =======================================================

    # project level
    project_resting_soc_5m = calc_field(resting_soc)(
        Required(Clean.project_soc_5m),
    )

    # bank level

    bank_resting_soc_5m = calc_field(resting_soc)(
        Required(Clean.bank_soc_5m),
    )

    # block level

    block_resting_soc_5m = calc_field(resting_soc)(
        Required(Clean.block_soc_5m),
    )

    # string level

    string_resting_soc_5m = calc_field(resting_soc)(
        Required(Clean.string_soc_5m),
    )

    # =======================================================
    # Other
    # =======================================================

    project_soh_5m = calc_field(mean_across_devices)(
        Required(Clean.string_soh_5m),
        device_type=Constant(DeviceTypeEnum.BESS_STRING),
    )

    # =======================================================
    # Events
    # =======================================================

    # Project

    project_available_5m = calc_field(available_from_event)(
        event_change=Required(Clean.project_offline_event_change_5m),
    )

    # PCS

    pcs_available_5m = calc_field(available_from_event)(
        event_change=Required(Clean.pcs_offline_event_change_5m),
    )

    # PCS Module

    pcs_module_available_5m = calc_field(available_from_event)(
        event_change=Required(Clean.pcs_module_offline_event_change_5m),
    )

    # =======================================================
    # Availability
    # =======================================================

    project_pcs_availability_5m = calc_field(mean_across_devices)(
        Required(pcs_available_5m),
        device_type=Constant(DeviceTypeEnum.BESS_PCS),
    )

    @method_calc(
        project_pcs_availability=Required(project_pcs_availability_5m),
        project_available=Required(project_available_5m),
    )
    def project_system_availability_5m(
        project_pcs_availability: xr.DataArray,
        project_available: xr.DataArray,
    ) -> xr.DataArray:
        """
        Project System Availability Per 5-Minute Interval
        If the project is offline, then the system availability is 0.
        Otherwise, the system availability is project level pcs availability
        """
        return project_pcs_availability * project_available

    @method_calc(
        availability=Required(project_system_availability_5m),
        soh=Required(project_soh_5m),
        energy_capacity=Required(Clean.project_energy_capacity_kwh),
    )
    def project_energy_availability_5m(
        availability: xr.DataArray,
        soh: xr.DataArray,
        energy_capacity: xr.DataArray,
    ) -> xr.DataArray:
        """
        Project Energy Availability Per 5-Minute Interval
        system availability multiplied by project SOH and energy capacity.
        """
        return availability * soh * energy_capacity

    @method_calc(
        availability=Required(project_system_availability_5m),
        power_capacity=Required(Clean.project_power_capacity_kw),
        poi_capacity=Required(Clean.project_poi_limit_kw),
    )
    def project_power_availability_5m(
        availability: xr.DataArray,
        power_capacity: xr.DataArray,
        poi_capacity: xr.DataArray,
    ) -> xr.DataArray:
        """
        Project Power Availability Per 5-Minute Interval
        availability times power capacity, clipped at POI capacity
        """
        return (availability * power_capacity).clip(max=poi_capacity)

    @method_calc(
        availability_5m=Required(project_system_availability_5m),
        hour_utc_5m=Grouper(hour_utc_5m),
    )
    def project_ner_availability_h(
        availability_5m: xr.DataArray,
        hour_utc_5m: xr.DataArray,
    ) -> xr.DataArray:
        """
        Project NER Availability Per Hour
        Used for excel report.
        Determine hours with perfect availability.
        Any offline underperformance event prevents the project
        from discharging at nameplate power (required by
        Technical Performance Metrics in Exhibit 7) making it
        an exclusion. See Section III bb.
        Periods with missing availability data are excluded
        from the calculation.
        If at at least 30 minutes of the hour has perfect availability,
        the whole hour is assigned a 1.0.
        """
        epsilon = 1e-6
        perfect_availability = xr.where(
            availability_5m >= 1 - epsilon,
            1.0,
            xr.where(availability_5m < 1 - epsilon, 0.0, np.nan),
        )
        num_perfect_intervals = resample_sum(perfect_availability, grouper=hour_utc_5m)
        # if at least 6 perfect 5-minute intervals, than the hour is considered
        # NER available.
        return xr.where(
            num_perfect_intervals >= 6,
            1.0,
            xr.where(num_perfect_intervals < 6, 0.0, np.nan),
        )

    # =======================================================
    # Charing Discharging Idling
    # =======================================================

    # project level

    project_is_charging_5m = calc_field(is_charging)(
        c_rate=Required(project_c_rate_5m),
    )

    project_is_discharging_5m = calc_field(is_discharging)(
        c_rate=Required(project_c_rate_5m),
    )

    project_is_idling_5m = calc_field(is_idling)(
        c_rate=Required(project_c_rate_5m),
    )

    # pcs level

    pcs_is_charging_5m = calc_field(is_charging)(
        c_rate=Required(pcs_c_rate_5m),
    )

    pcs_is_discharging_5m = calc_field(is_discharging)(
        c_rate=Required(pcs_c_rate_5m),
    )

    pcs_is_idling_5m = calc_field(is_idling)(
        c_rate=Required(pcs_c_rate_5m),
    )

    # pcs power

    pcs_power_while_charging_5m = calc_field(where)(
        Required(Clean.pcs_power_kw_5m),
        condition=Required(project_is_charging_5m),
    )

    pcs_power_while_discharging_5m = calc_field(where)(
        Required(Clean.pcs_power_kw_5m),
        condition=Required(project_is_discharging_5m),
    )
