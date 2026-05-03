import xarray as xr
from kpi.base.enumeration import TimeCoords
from kpi.base.exception import ValidationError
from kpi.base.protocol import CalcProtocol
from kpi.domain.util import (
    apply_filter,
    diff,
    fill_accumulator,
    filter_capacity,
    filter_tracker,
    filter_verify,
    verify_positive,
)
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.arg import Constant, Required
from kpi.op.transform.method import calc_field, method_calc
from kpi.registry.download.device.pv.attribute import (
    DownloadDevicePvAttribute as Device,
)
from kpi.registry.download.project_attribute.pv import (
    DownloadProjectAttributePv as Project,
)
from kpi.registry.download.sensor.api import DownloadSensor as Sensor


class TransformPvClean(FieldRegistry[CalcProtocol]):
    # =======================================================
    # Project Attributes
    # =======================================================

    project_total_delivered_energy_filled_kwh_5m = calc_field(fill_accumulator)(
        Required(Sensor.project_total_delivered_energy_raw_kwh_5m),
    )

    inverter_total_energy_production_filled_kwh_5m = calc_field(fill_accumulator)(
        Required(Sensor.inverter_total_energy_production_raw_kwh_5m),
    )

    @method_calc(
        value=Required(Project.project_latitude_raw_deg),
    )
    def project_latitude_deg(
        value: xr.DataArray,
    ) -> xr.DataArray:
        if value.item() == 0:
            raise ValidationError("Project latitude is 0")
        return filter_verify(filter_by=value, min_value=-90, max_value=90)

    @method_calc(
        value=Required(Project.project_longitude_raw_deg),
    )
    def project_longitude_deg(
        value: xr.DataArray,
    ) -> xr.DataArray:
        if value.item() == 0:
            raise ValidationError("Project longitude is 0")
        return filter_verify(filter_by=value, min_value=-180, max_value=180)

    project_elevation_m = calc_field(filter_verify)(
        filter_by=Required(Project.project_elevation_raw_m),
        min_value=Constant(1),
        max_value=Constant(10000),
    )

    # Capacity validations
    project_dc_capacity_kw = calc_field(verify_positive)(
        Required(Project.project_dc_capacity_raw_kw),
    )

    # =======================================================
    # Device Attributes
    # =======================================================

    combiner_dc_capacity_kw = calc_field(verify_positive)(
        Required(Device.combiner_dc_capacity_raw_kw),
    )

    inverter_ac_capacity_kw = calc_field(verify_positive)(
        Required(Device.inverter_ac_capacity_raw_kw),
    )

    inverter_dc_capacity_kw = calc_field(verify_positive)(
        Required(Device.inverter_dc_capacity_raw_kw),
    )

    inverter_module_ac_capacity_kw = calc_field(verify_positive)(
        Required(Device.inverter_module_ac_capacity_raw_kw),
    )

    # =======================================================
    # Sensors
    # =======================================================

    pv_project_power_kw_5m = calc_field(filter_capacity)(
        value=Required(Sensor.project_power_raw_kw_5m),
        capacity=Required(project_dc_capacity_kw),
    )

    @method_calc(
        x=Required(Sensor.met_poa_irradiance_raw_w_m2_5m),
    )
    def met_poa_irradiance_w_m2_5m(
        x: xr.DataArray,
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

    inverter_ac_power_kw_5m = calc_field(filter_capacity)(
        value=Required(Sensor.inverter_ac_power_raw_kw_5m),
        capacity=Required(inverter_ac_capacity_kw),
    )

    inverter_reactive_power_kvar_5m = calc_field(filter_capacity)(
        value=Required(Sensor.inverter_reactive_power_raw_kvar_5m),
        capacity=Required(inverter_dc_capacity_kw),
    )

    inverter_ac_power_setpoint_kw_5m = calc_field(filter_capacity)(
        value=Required(Sensor.inverter_ac_power_setpoint_raw_kw_5m),
        capacity=Required(inverter_dc_capacity_kw),
    )

    inverter_module_ac_power_kw_5m = calc_field(filter_capacity)(
        value=Required(Sensor.inverter_module_ac_power_raw_kw_5m),
        capacity=Required(inverter_module_ac_capacity_kw),
    )

    project_power_setpoint_kw_5m = calc_field(filter_capacity)(
        value=Required(Sensor.project_power_setpoint_raw_kw_5m),
        capacity=Required(project_dc_capacity_kw),
    )

    # tracker validation
    tracker_row_position_deg_5m = calc_field(filter_tracker)(
        Required(Sensor.tracker_row_position_raw_deg_5m),
    )

    tracker_row_setpoint_deg_5m = calc_field(filter_tracker)(
        Required(Sensor.tracker_row_setpoint_raw_deg_5m),
    )

    # voltage validation
    inverter_voltage_v_5m = calc_field(apply_filter)(
        Required(Sensor.inverter_voltage_raw_v_5m),
        min_value=Constant(0),
        max_value=Constant(2000),
    )

    inverter_module_voltage_v_5m = calc_field(apply_filter)(
        Required(Sensor.inverter_module_voltage_raw_v_5m),
        min_value=Constant(0),
        max_value=Constant(2000),
    )
