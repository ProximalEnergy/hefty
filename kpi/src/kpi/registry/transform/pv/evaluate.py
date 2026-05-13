import numpy as np
import pandas as pd
import xarray as xr
from core.enumerations import DeviceTypeEnum
from kpi.base.enumeration import TimeCoord
from kpi.base.protocol import CalcProtocol
from kpi.base.util import coord
from kpi.domain.agg.across_devices import mean_across_devices
from kpi.domain.agg.resample import resample_diff, resample_sum
from kpi.domain.general import filter_energy_5m
from kpi.domain.util import (
    diff,
    fill_na_with_arrays,
)
from kpi.infra.pvlib_integration import theoretical_poa_irradiance
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.arg import (
    Constant,
    Grouper,
    Optional,
    Required,
    TimeCoordArg,
    TimeZone,
)
from kpi.op.transform.method import calc_field, method_calc
from kpi.registry.download.device.pv.hierarchy import DownloadDevicePvHierarchy
from kpi.registry.download.expected_energy import DownloadExpectedEnergy as Expected
from kpi.registry.download.sensor.pv import DownloadSensorPv
from kpi.registry.transform.hybrid.api import date_local_5m
from kpi.registry.transform.pv.clean import TransformPvClean as Clean


class TransformPvEvaluate(FieldRegistry[CalcProtocol]):
    @method_calc(
        time_5m_utc=TimeCoordArg(TimeCoord.TIME_5MIN_UTC),
        time_zone=TimeZone(),
    )
    def time_local_5m(
        time_5m_utc: pd.DatetimeIndex,
        time_zone: str,
    ) -> xr.DataArray:
        local_time = (
            time_5m_utc.tz_localize("UTC").tz_convert(time_zone).tz_localize(None)
        )
        return xr.DataArray(
            local_time.values,
            dims=[TimeCoord.TIME_5MIN_UTC.value],
            coords={TimeCoord.TIME_5MIN_UTC.value: time_5m_utc},
        )

    project_energy_exported_to_grid_unfiltered_kwh_5m = calc_field(diff)(
        Required(Clean.project_total_energy_exported_to_grid_filled_kwh_5m),
    )

    project_energy_exported_to_grid_kwh_5m = calc_field(filter_energy_5m)(
        energy_unfiltered_5m=Required(
            project_energy_exported_to_grid_unfiltered_kwh_5m
        ),
        power_capacity=Required(Clean.project_ac_power_capacity_kw),
    )

    project_energy_production_unfiltered_kwh_d = calc_field(resample_diff)(
        Required(Clean.project_total_energy_exported_to_grid_filled_kwh_5m),
        grouper=Grouper(date_local_5m),
    )

    inverter_energy_production_unfiltered_kwh_d = calc_field(resample_diff)(
        Required(Clean.inverter_total_energy_production_filled_kwh_5m),
        grouper=Grouper(date_local_5m),
    )

    project_expected_energy_best_kwh_5m = calc_field(fill_na_with_arrays)(
        Optional(Expected.project_expected_energy_degraded_soiled_kwh_5m),
        Optional(Expected.project_expected_energy_degraded_kwh_5m),
        Optional(Expected.project_expected_energy_soiled_kwh_5m),
        Optional(Expected.project_expected_energy_kwh_5m),
    )

    combiner_expected_energy_best_kwh_5m = calc_field(fill_na_with_arrays)(
        Optional(Expected.combiner_expected_energy_degraded_soiled_kwh_5m),
        Optional(Expected.combiner_expected_energy_degraded_kwh_5m),
        Optional(Expected.combiner_expected_energy_soiled_kwh_5m),
        Optional(Expected.combiner_expected_energy_kwh_5m),
    )

    project_poa_irradiance_w_m2_5m = calc_field(mean_across_devices)(
        Required(Clean.met_poa_irradiance_w_m2_5m),
        device_type=Constant(DeviceTypeEnum.MET_STATION),
    )

    @method_calc(
        irradiance=Required(project_poa_irradiance_w_m2_5m),
        date_local_5m=Grouper(date_local_5m),
    )
    def project_insolation_d(
        irradiance: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return resample_sum(irradiance, grouper=date_local_5m) / 12

    @method_calc(
        power=Required(Clean.inverter_ac_power_kw_5m),
        met_poa=Required(Clean.met_poa_irradiance_w_m2_5m),
    )
    def inverter_mechanical_availability_5m(
        power: xr.DataArray,
        met_poa: xr.DataArray,
    ) -> xr.DataArray:
        minimum_irradiance = 10
        poa_threshold = 90
        epsilon = 1e-6
        project_mean_irradiance = met_poa.where(met_poa >= minimum_irradiance).mean(
            dim=coord(DeviceTypeEnum.MET_STATION)
        )
        power_filtered = power.where(project_mean_irradiance > poa_threshold)

        return xr.where(
            power_filtered > epsilon,
            1.0,
            xr.where(power_filtered < epsilon, 0.0, np.nan),
        )

    @method_calc(
        pcs_power=Required(Clean.inverter_ac_power_kw_5m),
        combiner_current=Required(DownloadSensorPv.combiner_current_raw_amps_5m),
        combiner_to_inverter=Required(DownloadDevicePvHierarchy.combiner_to_inverter),
        met_poa=Required(Clean.met_poa_irradiance_w_m2_5m),
    )
    def combiner_mechanical_availability_5m(
        pcs_power: xr.DataArray,
        combiner_current: xr.DataArray,
        combiner_to_inverter: xr.DataArray,
        met_poa: xr.DataArray,
    ) -> xr.DataArray:
        minimum_irradiance = 10
        poa_threshold = 90
        current_threshold_amps = 10
        pcs_power_threshold = 5
        project_mean_irradiance = met_poa.where(met_poa >= minimum_irradiance).mean(
            dim=coord(DeviceTypeEnum.MET_STATION)
        )

        power_broadcasted = pcs_power.sel(
            {coord(DeviceTypeEnum.PV_INVERTER): combiner_to_inverter}
        ).drop_vars(coord(DeviceTypeEnum.PV_INVERTER))

        is_valid = (project_mean_irradiance > poa_threshold) & (
            power_broadcasted > pcs_power_threshold
        )

        is_available = (combiner_current > current_threshold_amps) & is_valid

        return xr.where(is_available, 1.0, xr.where(is_valid, 0.0, np.nan))

    @method_calc(
        position=Required(Clean.tracker_row_position_deg_5m),
        setpoint=Required(Clean.tracker_row_setpoint_deg_5m),
    )
    def tracker_row_is_available_5m(
        position: xr.DataArray,
        setpoint: xr.DataArray,
    ) -> xr.DataArray:
        threshold_deg = 2
        difference = abs(position - setpoint)
        return xr.where(
            difference <= threshold_deg,
            1.0,
            xr.where(difference > threshold_deg, 0.0, np.nan),
        )

    project_theoretical_poa_irradiance_w_m2_5m = calc_field(theoretical_poa_irradiance)(
        time_utc=TimeCoordArg(TimeCoord.TIME_5MIN_UTC),
        latitude=Required(Clean.project_latitude_deg),
        longitude=Required(Clean.project_longitude_deg),
        altitude_m=Optional(Clean.project_elevation_m),
        time_zone=TimeZone(),
    )

    @method_calc(
        position=Required(Clean.tracker_row_position_deg_5m),
        setpoint=Required(Clean.tracker_row_setpoint_deg_5m),
    )
    def tracker_row_deviation_from_setpoint_deg_5m(
        position: xr.DataArray,
        setpoint: xr.DataArray,
    ) -> xr.DataArray:
        return abs(position - setpoint)

    @method_calc(
        setpoint=Required(Clean.tracker_row_setpoint_deg_5m),
    )
    def tracker_row_setpoint_deviation_from_median_deg_5m(
        setpoint: xr.DataArray,
    ) -> xr.DataArray:
        return abs(setpoint - setpoint.median(dim=coord(DeviceTypeEnum.TRACKER_ROW)))
