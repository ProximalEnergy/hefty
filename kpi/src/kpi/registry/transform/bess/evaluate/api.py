import pandas as pd
import xarray as xr
from core.enumerations import DeviceTypeEnum
from kpi.base.enumeration import NEW_NAME, TimeCoords
from kpi.base.protocol import CalcProtocol
from kpi.domain.agg.across_devices import mean_across_devices, sum_across_devices
from kpi.domain.bess import (
    c_rate,
    c_rate_while_charging,
    c_rate_while_discharging,
    energy_5m_from_accumulator,
    is_charging,
    is_discharging,
    is_idling,
    resting_soc,
)
from kpi.domain.util import (
    available_from_event,
    fill_accumulator,
    where,
)
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.arg import Constant, Required, Time5MinUtc, TimeZone
from kpi.op.transform.method import calc_field, method_calc
from kpi.registry.download.sensor.bess import DownloadSensorBess
from kpi.registry.transform.bess.clean.api import TransformBessClean as Clean


class TransformBessEvaluate(FieldRegistry[CalcProtocol]):
    @method_calc(
        time_utc=Time5MinUtc(),
        time_zone=TimeZone(),
    )
    def date_local_5m(
        time_utc: pd.DatetimeIndex,
        time_zone: str,
    ) -> xr.DataArray:
        """
        Local date taking into account time zone and daylight savings
        for each 5-minute UTC time stamp.
        """

        local_time = time_utc.tz_localize("UTC").tz_convert(time_zone).tz_localize(None)
        date_local = local_time.floor("D").to_numpy()
        return xr.DataArray(
            date_local,
            dims=[TimeCoords.TIME_5MIN_UTC.value],
            coords={TimeCoords.TIME_5MIN_UTC.value: time_utc},
            attrs={
                NEW_NAME: TimeCoords.DATE_LOCAL.value,
            },
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

    project_energy_charged_kwh_5m = calc_field(energy_5m_from_accumulator)(
        accumulator=Required(project_total_energy_charged_filled_kwh_5m),
        power_capacity=Required(Clean.project_power_capacity_kw),
    )

    project_energy_discharged_kwh_5m = calc_field(energy_5m_from_accumulator)(
        accumulator=Required(project_total_energy_discharged_filled_kwh_5m),
        power_capacity=Required(Clean.project_power_capacity_kw),
    )

    # PCS level

    pcs_energy_charged_kwh_5m = calc_field(energy_5m_from_accumulator)(
        accumulator=Required(pcs_total_energy_charged_filled_kwh_5m),
        power_capacity=Required(Clean.pcs_power_capacity_kw),
    )

    project_pcs_energy_charged_kwh_5m = calc_field(sum_across_devices)(
        Required(pcs_energy_charged_kwh_5m),
        device_type=Constant(DeviceTypeEnum.BESS_PCS),
    )

    pcs_energy_discharged_kwh_5m = calc_field(energy_5m_from_accumulator)(
        accumulator=Required(pcs_total_energy_discharged_filled_kwh_5m),
        power_capacity=Required(Clean.pcs_power_capacity_kw),
    )

    project_pcs_energy_discharged_kwh_5m = calc_field(sum_across_devices)(
        Required(pcs_energy_discharged_kwh_5m),
        device_type=Constant(DeviceTypeEnum.BESS_PCS),
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
