import numpy as np
import xarray as xr
from core.enumerations import DeviceTypeEnum
from kpi.base.protocol import CalcProtocol
from kpi.base.util import coord
from kpi.domain.util import date_local, diff, filter_mask
from kpi.op.field import Field
from kpi.op.field_registry import FieldRegistry
from kpi.op.time import TimeLocal
from kpi.op.transform.class_calc import TheoreticalPoaIrradiance
from kpi.op.transform.input import Optional, Required
from kpi.op.transform.method import method_calc
from kpi.registry.download.device.pv.hierarchy import DownloadDevicePvHierarchy
from kpi.registry.download.expected_energy import DownloadExpectedEnergy as Expected
from kpi.registry.download.sensor.pv import DownloadSensorPv
from kpi.registry.transform.hybrid.api import date_local_5m
from kpi.registry.transform.pv.clean import TransformPvClean as Clean


class TransformPvEvaluate(FieldRegistry[CalcProtocol]):
    time_local_5m = Field[CalcProtocol](TimeLocal())

    @method_calc(
        total=Required(Clean.project_total_delivered_energy_filled_kwh_5m),
        power_capacity=Required(Clean.project_dc_capacity_kw),
    )
    def project_delivered_energy_kwh_5m(
        total: xr.DataArray,
        power_capacity: xr.DataArray,
    ) -> xr.DataArray:
        energy = diff(total)
        return energy.where(
            filter_mask(filter_by=energy / power_capacity, min_value=0, max_value=1)
        )

    @method_calc(
        first=Optional(Expected.project_expected_power_degraded_soiled_kw_5m),
        second=Optional(Expected.project_expected_power_degraded_kw_5m),
        third=Optional(Expected.project_expected_power_soiled_kw_5m),
        fourth=Optional(Expected.project_expected_power_kw_5m),
    )
    def project_expected_energy_best_kw_5m(
        first: xr.DataArray | None,
        second: xr.DataArray | None,
        third: xr.DataArray | None,
        fourth: xr.DataArray | None,
    ) -> xr.DataArray:
        x = xr.DataArray(np.nan)
        for y in [first, second, third, fourth]:
            if y is not None:
                x, y = xr.align(x, y, join="outer")
                x = x.fillna(y)
        return x / 12  # because there are 12 5 minute intervals in an hour

    @method_calc(
        first=Optional(Expected.combiner_expected_power_degraded_soiled_kw_5m),
        second=Optional(Expected.combiner_expected_power_degraded_kw_5m),
        third=Optional(Expected.combiner_expected_power_soiled_kw_5m),
        fourth=Optional(Expected.combiner_expected_power_kw_5m),
    )
    def combiner_expected_energy_best_kwh_5m(
        first: xr.DataArray | None,
        second: xr.DataArray | None,
        third: xr.DataArray | None,
        fourth: xr.DataArray | None,
    ) -> xr.DataArray:
        x = xr.DataArray(np.nan)
        for y in [first, second, third, fourth]:
            if y is not None:
                x, y = xr.align(x, y, join="outer")
                x = x.fillna(y)
        return x / 12  # because there are 12 5 minute intervals in an hour

    @method_calc(
        irradiance=Required(Clean.met_poa_irradiance_w_m2_5m),
    )
    def project_poa_irradiance_w_m2_5m(
        irradiance: xr.DataArray,
    ) -> xr.DataArray:
        return irradiance.mean(dim=coord(DeviceTypeEnum.MET_STATION))

    @method_calc(
        irradiance=Required(project_poa_irradiance_w_m2_5m),
        date_local_5m=Required(date_local_5m),
    )
    def project_insolation_d(
        irradiance: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return irradiance.groupby(date_local(date_local_5m)).sum() / 12

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

    project_theoretical_poa_irradiance_w_m2_5m = Field[CalcProtocol](
        TheoreticalPoaIrradiance(
            project_latitude_deg=Required(Clean.project_latitude_deg),
            project_longitude_deg=Required(Clean.project_longitude_deg),
            project_elevation_m=Optional(Clean.project_elevation_m),
        )
    )
