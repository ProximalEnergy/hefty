import xarray as xr
from kpi.base.enumeration import TimeCoords
from kpi.base.exception import ValidationError
from kpi.domain.util import (
    diff,
    filter_capacity,
    filter_mask,
    filter_tracker,
    filter_verify,
    verify_positive,
)
from kpi.service.transform.method import Input, method_calc
from kpi.service.transform.schema import CalcSchema
from kpi.service.transform.unary import unary_field
from kpi.workflow.download.device.pv.attribute import (
    DownloadDevicePvAttribute as Device,
)
from kpi.workflow.download.project_attribute.pv import (
    DownloadProjectAttributePv as Project,
)
from kpi.workflow.download.sensor.workflow import DownloadSensor as Sensor


class TransformPvClean(CalcSchema):
    # =======================================================
    # Project Attributes
    # =======================================================

    @method_calc
    def project_total_delivered_energy_filled_kwh_5m(
        value: xr.DataArray = Input(Sensor.project_total_delivered_energy_raw_kwh_5m),
    ) -> xr.DataArray:
        return value.ffill(dim=TimeCoords.TIME_5MIN_UTC.value).bfill(
            dim=TimeCoords.TIME_5MIN_UTC.value
        )

    @method_calc
    def inverter_total_energy_production_filled_kwh_5m(
        value: xr.DataArray = Input(Sensor.inverter_total_energy_production_raw_kwh_5m),
    ) -> xr.DataArray:
        return value.ffill(dim=TimeCoords.TIME_5MIN_UTC.value).bfill(
            dim=TimeCoords.TIME_5MIN_UTC.value
        )

    @method_calc
    def project_latitude_deg(
        value: xr.DataArray = Input(Project.project_latitude_raw_deg),
    ) -> xr.DataArray:
        if value.item() == 0:
            raise ValidationError("Project latitude is 0")
        return filter_verify(filter_by=value, min_value=-90, max_value=90)

    @method_calc
    def project_longitude_deg(
        value: xr.DataArray = Input(Project.project_longitude_raw_deg),
    ) -> xr.DataArray:
        if value.item() == 0:
            raise ValidationError("Project longitude is 0")
        return filter_verify(filter_by=value, min_value=-180, max_value=180)

    @method_calc
    def project_elevation_m(
        value: xr.DataArray = Input(Project.project_elevation_raw_m),
    ) -> xr.DataArray:
        return filter_verify(filter_by=value, min_value=1, max_value=10000)

    # Capacity validations
    project_dc_capacity_kw = unary_field(
        verify_positive,
        field=Project.project_dc_capacity_raw_kw,
    )

    project_poi_limit_kw = unary_field(
        verify_positive,
        field=Project.project_poi_limit_raw_kw,
    )

    # =======================================================
    # Device Attributes
    # =======================================================

    combiner_dc_capacity_kw = unary_field(
        verify_positive,
        field=Device.combiner_dc_capacity_raw_kw,
    )

    inverter_ac_capacity_kw = unary_field(
        verify_positive,
        field=Device.inverter_ac_capacity_raw_kw,
    )

    inverter_dc_capacity_kw = unary_field(
        verify_positive,
        field=Device.inverter_dc_capacity_raw_kw,
    )

    inverter_module_ac_capacity_kw = unary_field(
        verify_positive,
        field=Device.inverter_module_ac_capacity_raw_kw,
    )

    # =======================================================
    # Sensors
    # =======================================================

    @method_calc
    def pv_project_power_kw_5m(
        power: xr.DataArray = Input(Sensor.project_power_raw_kw_5m),
        capacity: xr.DataArray = Input(project_dc_capacity_kw),
    ) -> xr.DataArray:
        return power.where(
            filter_mask(filter_by=power / capacity, min_value=-1e-6, max_value=1)
        )

    @method_calc
    def met_poa_irradiance_w_m2_5m(
        x: xr.DataArray = Input(Sensor.met_poa_irradiance_raw_w_m2_5m),
    ) -> xr.DataArray:
        window_size = 6  # flat lining for 30 minutes
        epsilon = 1e-6

        diffs = abs(diff(x, time_dim=TimeCoords.TIME_5MIN_UTC))

        flat_mask = (
            diffs.rolling({TimeCoords.TIME_5MIN_UTC.value: window_size - 1}).max()
            < epsilon
        )

        return x.where(~flat_mask)

    # power validation

    @method_calc
    def inverter_ac_power_kw_5m(
        value: xr.DataArray = Input(Sensor.inverter_ac_power_raw_kw_5m),
        capacity: xr.DataArray = Input(inverter_ac_capacity_kw),
    ) -> xr.DataArray:
        return filter_capacity(
            value=value,
            capacity=capacity,
        )

    @method_calc
    def inverter_reactive_power_kvar_5m(
        value: xr.DataArray = Input(Sensor.inverter_reactive_power_raw_kvar_5m),
        capacity: xr.DataArray = Input(inverter_dc_capacity_kw),
    ) -> xr.DataArray:
        return filter_capacity(
            value=value,
            capacity=capacity,
        )

    @method_calc
    def inverter_module_ac_power_kw_5m(
        value: xr.DataArray = Input(Sensor.inverter_module_ac_power_raw_kw_5m),
        capacity: xr.DataArray = Input(inverter_module_ac_capacity_kw),
    ) -> xr.DataArray:
        return filter_capacity(
            value=value,
            capacity=capacity,
        )

    @method_calc
    def project_power_setpoint_kw_5m(
        value: xr.DataArray = Input(Sensor.project_power_setpoint_raw_kw_5m),
        capacity: xr.DataArray = Input(project_dc_capacity_kw),
    ) -> xr.DataArray:
        return filter_capacity(
            value=value,
            capacity=capacity,
        )

    @method_calc
    def inverter_ac_power_setpoint_kw_5m(
        value: xr.DataArray = Input(Sensor.inverter_ac_power_setpoint_raw_kw_5m),
        capacity: xr.DataArray = Input(inverter_dc_capacity_kw),
    ) -> xr.DataArray:
        return filter_capacity(
            value=value,
            capacity=capacity,
        )

    # tracker validation
    tracker_row_position_deg_5m = unary_field(
        filter_tracker,
        field=Sensor.tracker_row_position_raw_deg_5m,
    )

    tracker_row_setpoint_deg_5m = unary_field(
        filter_tracker,
        field=Sensor.tracker_row_setpoint_raw_deg_5m,
    )

    # voltage validation
    @method_calc
    def inverter_voltage_v_5m(
        voltage: xr.DataArray = Input(Sensor.inverter_voltage_raw_v_5m),
    ) -> xr.DataArray:
        return voltage.where(
            filter_mask(filter_by=voltage, min_value=0, max_value=2000)
        )

    @method_calc
    def inverter_module_voltage_v_5m(
        voltage: xr.DataArray = Input(Sensor.inverter_module_voltage_raw_v_5m),
    ) -> xr.DataArray:
        return voltage.where(
            filter_mask(filter_by=voltage, min_value=0, max_value=2000)
        )
