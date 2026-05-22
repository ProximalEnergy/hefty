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
    perfect_availability_intervals,
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
from kpi.op.transform.method import calc_field
from kpi.registry.download.sensor.bess import DownloadSensorBess
from kpi.registry.transform.bess.clean.api import TransformBessClean as Clean


def project_energy_availability_5m(
    *,
    project_pcs_availability: xr.DataArray,
    project_available: xr.DataArray,
) -> xr.DataArray:
    """Project energy availability from PCS availability and project online state.

    Args:
        project_pcs_availability: Mean PCS availability at 5-minute resolution.
        project_available: Project online flag at 5-minute resolution.

    Returns:
        Zero when offline; otherwise PCS availability.
    """
    return project_pcs_availability * project_available


def project_available_power_5m(
    *,
    available_charge: xr.DataArray,
    available_discharge: xr.DataArray,
) -> xr.DataArray:
    """Project available power as sum of per-PCS max charge/discharge.

    Args:
        available_charge: Clipped available charge power per PCS.
        available_discharge: Clipped available discharge power per PCS.

    Returns:
        Sum across PCS of ``fmax(charge, discharge)`` per interval.
    """
    available_power = xr.apply_ufunc(
        np.fmax,
        available_charge,
        available_discharge,
    )
    return sum_across_devices(available_power, device_type=DeviceTypeEnum.BESS_PCS)


def project_power_availability_5m(
    *,
    available_power: xr.DataArray,
    pcs_capacity: xr.DataArray,
) -> xr.DataArray:
    """Normalize project available power by total PCS capacity.

    Args:
        available_power: Project available power at 5-minute resolution.
        pcs_capacity: Per-PCS nameplate power capacity.

    Returns:
        ``available_power / sum(pcs_capacity)``.
    """
    total_capacity = sum_across_devices(
        pcs_capacity, device_type=DeviceTypeEnum.BESS_PCS
    )
    return available_power / total_capacity


def project_poi_power_availability_5m(
    *,
    available_power: xr.DataArray,
    poi_capacity: xr.DataArray,
) -> xr.DataArray:
    """Normalize POI-clipped available power by the POI limit.

    Args:
        available_power: Project available power at 5-minute resolution.
        poi_capacity: Point-of-interconnection power limit.

    Returns:
        ``clip(available_power, max=poi_capacity) / poi_capacity``.
    """
    clipped = available_power.clip(max=poi_capacity)
    return clipped / poi_capacity


def project_ner_availability_h(
    *,
    availability_5m: xr.DataArray,
    hour_utc_5m: xr.DataArray,
    min_perfect_intervals: int = 6,
    epsilon: float = 1e-6,
) -> xr.DataArray:
    """Hourly project NER availability (0/1) for Excel reporting.

    Flags hours with at least six perfect 5-minute intervals at availability
    ``>= 1 - epsilon``; otherwise ``0.0``. Missing availability yields NaN when
    no finite intervals remain.

    Args:
        availability_5m: Project energy availability at 5-minute resolution.
        hour_utc_5m: UTC hour grouper aligned to the time dimension.
        min_perfect_intervals: Minimum perfect intervals for an available hour.
        epsilon: Tolerance for perfect availability intervals.

    Returns:
        ``1.0``, ``0.0``, or NaN per UTC hour.
    """
    perfect = perfect_availability_intervals(availability_5m, epsilon=epsilon)
    num_perfect_intervals = resample_sum(perfect, grouper=hour_utc_5m)
    return xr.where(
        num_perfect_intervals >= min_perfect_intervals,
        1.0,
        xr.where(num_perfect_intervals < min_perfect_intervals, 0.0, np.nan),
    )


class TransformBessEvaluateKpi(FieldRegistry[CalcProtocol]):
    date_local_5m = calc_field(
        time_grouper, doc_header="Convert 5-minute UTC time to local date"
    )(
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

    project_energy_availability_5m = calc_field(project_energy_availability_5m)(
        project_pcs_availability=Required(project_pcs_availability_5m),
        project_available=Required(project_available_5m),
    )

    pcs_available_charge_power_clipped_kw_5m = calc_field(np.minimum)(
        Required(Clean.pcs_available_charge_power_kw_5m),
        Required(Clean.pcs_power_capacity_kw),
    )

    pcs_available_discharge_power_clipped_kw_5m = calc_field(np.minimum)(
        Required(Clean.pcs_available_discharge_power_kw_5m),
        Required(Clean.pcs_power_capacity_kw),
    )

    project_available_power_5m = calc_field(project_available_power_5m)(
        available_charge=Required(pcs_available_charge_power_clipped_kw_5m),
        available_discharge=Required(pcs_available_discharge_power_clipped_kw_5m),
    )

    project_power_availability_5m = calc_field(project_power_availability_5m)(
        available_power=Required(project_available_power_5m),
        pcs_capacity=Required(Clean.pcs_power_capacity_kw),
    )

    project_poi_power_availability_5m = calc_field(project_poi_power_availability_5m)(
        available_power=Required(project_available_power_5m),
        poi_capacity=Required(Clean.project_poi_limit_kw),
    )

    project_ner_availability_h = calc_field(project_ner_availability_h)(
        availability_5m=Required(project_energy_availability_5m),
        hour_utc_5m=Grouper(hour_utc_5m),
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
