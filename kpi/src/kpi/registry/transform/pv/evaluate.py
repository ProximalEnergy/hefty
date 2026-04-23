import numpy as np
import xarray as xr
from core.enumerations import DeviceType
from kpi.base.protocol import CalcProtocol
from kpi.base.util import coord
from kpi.domain.util import date_local, diff, filter_mask
from kpi.op.field_registry import FieldRegistry
from kpi.op.time import TimeLocal
from kpi.op.transform.class_calc import TheoreticalPoaIrradiance
from kpi.op.transform.method import calc_field, method_calc, optional, required
from kpi.registry.download.device.pv.hierarchy import DownloadDevicePvHierarchy
from kpi.registry.download.expected_energy import DownloadExpectedEnergy as Expected
from kpi.registry.download.sensor.pv import DownloadSensorPv
from kpi.registry.transform.hybrid.api import date_local_5m
from kpi.registry.transform.pv.clean import TransformPvClean as Clean


class TransformPvEvaluate(FieldRegistry[CalcProtocol]):
    time_local_5m = calc_field(TimeLocal())

    @method_calc
    def project_delivered_energy_kwh_5m(
        total: xr.DataArray = required(
            Clean.project_total_delivered_energy_filled_kwh_5m
        ),
        power_capacity: xr.DataArray = required(Clean.project_dc_capacity_kw),
    ) -> xr.DataArray:
        energy = diff(total)
        return energy.where(
            filter_mask(filter_by=energy / power_capacity, min_value=0, max_value=1)
        )

    @method_calc
    def project_expected_energy_best_kw_5m(
        first: xr.DataArray | None = optional(
            Expected.project_expected_power_degraded_soiled_kw_5m
        ),
        second: xr.DataArray | None = optional(
            Expected.project_expected_power_degraded_kw_5m
        ),
        third: xr.DataArray | None = optional(
            Expected.project_expected_power_soiled_kw_5m
        ),
        fourth: xr.DataArray | None = optional(Expected.project_expected_power_kw_5m),
    ) -> xr.DataArray:
        x = xr.DataArray(np.nan)
        for y in [first, second, third, fourth]:
            if y is not None:
                x, y = xr.align(x, y, join="outer")
                x = x.fillna(y)
        return x / 12  # because there are 12 5 minute intervals in an hour

    @method_calc
    def combiner_expected_energy_best_kwh_5m(
        first: xr.DataArray | None = optional(
            Expected.combiner_expected_power_degraded_soiled_kw_5m
        ),
        second: xr.DataArray | None = optional(
            Expected.combiner_expected_power_degraded_kw_5m
        ),
        third: xr.DataArray | None = optional(
            Expected.combiner_expected_power_soiled_kw_5m
        ),
        fourth: xr.DataArray | None = optional(Expected.combiner_expected_power_kw_5m),
    ) -> xr.DataArray:
        x = xr.DataArray(np.nan)
        for y in [first, second, third, fourth]:
            if y is not None:
                x, y = xr.align(x, y, join="outer")
                x = x.fillna(y)
        return x / 12  # because there are 12 5 minute intervals in an hour

    @method_calc
    def project_poa_irradiance_w_m2_5m(
        irradiance: xr.DataArray = required(Clean.met_poa_irradiance_w_m2_5m),
    ) -> xr.DataArray:
        return irradiance.mean(dim=coord(DeviceType.MET_STATION))

    @method_calc
    def project_insolation_d(
        irradiance: xr.DataArray = required(project_poa_irradiance_w_m2_5m),
        date_local_5m: xr.DataArray = required(date_local_5m),
    ) -> xr.DataArray:
        return irradiance.groupby(date_local(date_local_5m)).sum() / 12

    @method_calc
    def inverter_mechanical_availability_5m(
        power: xr.DataArray = required(Clean.inverter_ac_power_kw_5m),
        met_poa: xr.DataArray = required(Clean.met_poa_irradiance_w_m2_5m),
    ) -> xr.DataArray:
        minimum_irradiance = 10
        poa_threshold = 90
        epsilon = 1e-6
        project_mean_irradiance = met_poa.where(met_poa >= minimum_irradiance).mean(
            dim=coord(DeviceType.MET_STATION)
        )
        power_filtered = power.where(project_mean_irradiance > poa_threshold)

        return xr.where(
            power_filtered > epsilon,
            1.0,
            xr.where(power_filtered < epsilon, 0.0, np.nan),
        )

    @method_calc
    def combiner_mechanical_availability_5m(
        pcs_power: xr.DataArray = required(Clean.inverter_ac_power_kw_5m),
        combiner_current: xr.DataArray = required(
            DownloadSensorPv.combiner_current_raw_amps_5m
        ),
        combiner_to_inverter: xr.DataArray = required(
            DownloadDevicePvHierarchy.combiner_to_inverter
        ),
        met_poa: xr.DataArray = required(Clean.met_poa_irradiance_w_m2_5m),
    ) -> xr.DataArray:
        minimum_irradiance = 10
        poa_threshold = 90
        current_threshold_amps = 10
        pcs_power_threshold = 5
        project_mean_irradiance = met_poa.where(met_poa >= minimum_irradiance).mean(
            dim=coord(DeviceType.MET_STATION)
        )

        power_broadcasted = pcs_power.sel(
            {coord(DeviceType.PV_INVERTER): combiner_to_inverter}
        ).drop_vars(coord(DeviceType.PV_INVERTER))

        is_valid = (project_mean_irradiance > poa_threshold) & (
            power_broadcasted > pcs_power_threshold
        )

        is_available = (combiner_current > current_threshold_amps) & is_valid

        return xr.where(is_available, 1.0, xr.where(is_valid, 0.0, np.nan))

    @method_calc
    def tracker_row_is_available_5m(
        position: xr.DataArray = required(Clean.tracker_row_position_deg_5m),
        setpoint: xr.DataArray = required(Clean.tracker_row_setpoint_deg_5m),
    ) -> xr.DataArray:
        threshold_deg = 2
        difference = abs(position - setpoint)
        return xr.where(
            difference <= threshold_deg,
            1.0,
            xr.where(difference > threshold_deg, 0.0, np.nan),
        )

    project_theoretical_poa_irradiance_w_m2_5m = calc_field(
        TheoreticalPoaIrradiance(
            project_latitude_deg=Clean.project_latitude_deg.name,
            project_longitude_deg=Clean.project_longitude_deg.name,
            project_elevation_m=Clean.project_elevation_m.name,
        )
    )
