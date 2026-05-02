import xarray as xr
from core.enumerations import DeviceTypeEnum
from kpi.base.protocol import CalcProtocol
from kpi.domain.bess import resting_soc
from kpi.domain.util import coord, fill_accumulator
from kpi.op.field import Field
from kpi.op.field_registry import FieldRegistry
from kpi.op.time import DateLocal5m
from kpi.op.transform.class_calc import Energy5mFromAccumulator, Event
from kpi.op.transform.input import Required
from kpi.op.transform.method import method_calc
from kpi.op.transform.unary import unary_field
from kpi.registry.download.sensor.bess import DownloadSensorBess
from kpi.registry.transform.bess.clean.api import TransformBessClean as Clean


class TransformBessEvaluate(FieldRegistry[CalcProtocol]):
    date_local_5m = Field[CalcProtocol](DateLocal5m())

    # =======================================================
    # Backfill and forward fill accumulators to remove nans
    # =======================================================

    # project level

    project_total_energy_charged_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.project_total_energy_charged_raw_kwh_5m,
    )

    project_total_energy_discharged_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.project_total_energy_discharged_raw_kwh_5m,
    )

    project_total_aux_energy_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.project_total_aux_energy_raw_kwh_5m,
    )

    # mv circuit level

    circuit_total_energy_charged_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.circuit_total_energy_charged_raw_kwh_5m,
    )

    circuit_total_energy_discharged_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.circuit_total_energy_discharged_raw_kwh_5m,
    )

    # pcs level

    pcs_total_energy_charged_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.pcs_total_energy_charged_raw_kwh_5m,
    )

    pcs_total_energy_discharged_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.pcs_total_energy_discharged_raw_kwh_5m,
    )

    # pcs module level

    pcs_module_total_energy_charged_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.pcs_module_total_energy_charged_raw_kwh_5m,
    )

    pcs_module_total_energy_discharged_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.pcs_module_total_energy_discharged_raw_kwh_5m,
    )

    # string level

    string_total_energy_charged_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.string_total_energy_charged_raw_kwh_5m,
    )

    string_total_energy_discharged_filled_kwh_5m = unary_field(
        fill_accumulator,
        field=DownloadSensorBess.string_total_energy_discharged_raw_kwh_5m,
    )

    # =======================================================
    # Estimate 5-minute energy
    # =======================================================

    # Project level

    project_energy_charged_kwh_5m = Field[CalcProtocol](
        Energy5mFromAccumulator(
            accumulator=Required(project_total_energy_charged_filled_kwh_5m),
            power_capacity=Required(Clean.project_power_capacity_kw),
        )
    )

    project_energy_discharged_kwh_5m = Field[CalcProtocol](
        Energy5mFromAccumulator(
            accumulator=Required(project_total_energy_discharged_filled_kwh_5m),
            power_capacity=Required(Clean.project_power_capacity_kw),
        )
    )

    # PCS level

    pcs_energy_charged_dc_kwh_5m = Field[CalcProtocol](
        Energy5mFromAccumulator(
            accumulator=Required(pcs_total_energy_charged_filled_kwh_5m),
            power_capacity=Required(Clean.pcs_power_capacity_kw),
        )
    )

    pcs_energy_discharged_dc_kwh_5m = Field[CalcProtocol](
        Energy5mFromAccumulator(
            accumulator=Required(pcs_total_energy_discharged_filled_kwh_5m),
            power_capacity=Required(Clean.pcs_power_capacity_kw),
        )
    )

    # =======================================================
    # C-Rate
    # =======================================================

    # project level

    @method_calc(
        power=Required(Clean.project_power_kw_5m),
        energy_capacity=Required(Clean.project_energy_capacity_kwh),
    )
    def project_c_rate_5m(
        power: xr.DataArray,
        energy_capacity: xr.DataArray,
    ) -> xr.DataArray:
        return power / energy_capacity

    # pcs level

    @method_calc(
        power=Required(Clean.pcs_power_kw_5m),
        energy_capacity=Required(Clean.pcs_energy_capacity_kwh),
    )
    def pcs_c_rate_5m(
        power: xr.DataArray,
        energy_capacity: xr.DataArray,
    ) -> xr.DataArray:
        return power / energy_capacity

    # string level

    @method_calc(
        power=Required(Clean.string_power_kw_5m),
        energy_capacity=Required(Clean.string_energy_capacity_kwh),
    )
    def string_c_rate_5m(
        power: xr.DataArray,
        energy_capacity: xr.DataArray,
    ) -> xr.DataArray:
        return power / energy_capacity

    # =======================================================
    # Resting SOC
    # =======================================================

    # project level
    project_resting_soc_5m = unary_field(
        resting_soc,
        field=Clean.project_soc_5m,
    )

    # bank level

    bank_resting_soc_5m = unary_field(
        resting_soc,
        field=Clean.bank_soc_5m,
    )

    # block level

    block_resting_soc_5m = unary_field(
        resting_soc,
        field=Clean.block_soc_5m,
    )

    # string level

    string_resting_soc_5m = unary_field(
        resting_soc,
        field=Clean.string_soc_5m,
    )

    # =======================================================
    # Other
    # =======================================================

    @method_calc(
        soh=Required(Clean.string_soh_5m),
    )
    def project_soh_5m(
        soh: xr.DataArray,
    ) -> xr.DataArray:
        """
        Project SOH Per 5-Minute Interval
        average across all string devices for each 5-minute interval.
        String devices with missing SOH are excluded from the average.
        """
        return soh.mean(dim=coord(DeviceTypeEnum.BESS_STRING))

    # =======================================================
    # Events
    # =======================================================

    # Project

    project_offline_event_5m = Field[CalcProtocol](
        Event(
            event_change=Required(Clean.project_offline_event_change_5m),
        )
    )

    # PCS

    pcs_offline_event_5m = Field[CalcProtocol](
        Event(
            event_change=Required(Clean.pcs_offline_event_change_5m),
        )
    )

    # PCS Module

    pcs_module_offline_event_5m = Field[CalcProtocol](
        Event(
            event_change=Required(Clean.pcs_module_offline_event_change_5m),
        )
    )

    # =======================================================
    # Availability
    # =======================================================

    @method_calc(
        offline_event=Required(pcs_offline_event_5m),
    )
    def pcs_availability_5m(
        offline_event: xr.DataArray,
    ) -> xr.DataArray:
        """
        PCS Availability Per 5-Minute Interval
        1 - `offline_event`
        """
        return 1 - offline_event

    @method_calc(
        availability=Required(pcs_availability_5m),
    )
    def project_pcs_availability_5m(
        availability: xr.DataArray,
    ) -> xr.DataArray:
        """
        Project PCS Availability Per 5-Minute Interval
        average across all PCS devices for each 5-minute interval.
        """
        return availability.mean(dim=coord(DeviceTypeEnum.BESS_PCS))

    @method_calc(
        project_pcs_availability=Required(project_pcs_availability_5m),
        project_event=Required(project_offline_event_5m),
    )
    def project_system_availability_5m(
        project_pcs_availability: xr.DataArray,
        project_event: xr.DataArray,
    ) -> xr.DataArray:
        """
        Project System Availability Per 5-Minute Interval
        If the project is offline, then the system availability is 0.
        Otherwise, the system availability is project level pcs availability
        """
        project_availability = 1 - project_event
        return project_pcs_availability * project_availability

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
