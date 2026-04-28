import xarray as xr
from kpi.base.protocol import CalcProtocol
from kpi.domain.bess import clean_cell_voltage, clean_soc, clean_soh, clean_temperature
from kpi.domain.util import filter_mask
from kpi.op.field import Field
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.class_calc import BessCleanPower
from kpi.op.transform.input import Required
from kpi.op.transform.method import method_calc
from kpi.op.transform.unary import unary_field
from kpi.registry.download.sensor.bess import DownloadSensorBess as Sensor
from kpi.registry.transform.bess.clean.device_attribute import (
    TransformBessCleanDeviceAttribute as Device,
)
from kpi.registry.transform.bess.clean.project_attribute import (
    TransformBessCleanProjectAttribute as Project,
)


class TransformBessCleanSensor(FieldRegistry[CalcProtocol]):
    # =======================================================
    # Power
    # =======================================================

    # project level

    project_power_kw_5m = Field[CalcProtocol](
        BessCleanPower(
            power=Required(Sensor.project_power_raw_kw_5m),
            capacity=Required(Project.project_power_capacity_kw),
        )
    )

    # pcs level

    pcs_power_kw_5m = Field[CalcProtocol](
        BessCleanPower(
            power=Required(Sensor.pcs_power_raw_kw_5m),
            capacity=Required(Device.pcs_power_capacity_kw),
        )
    )

    # string
    string_power_kw_5m = Field[CalcProtocol](
        BessCleanPower(
            power=Required(Sensor.string_power_raw_kw_5m),
            capacity=Required(Device.string_power_capacity_kw),
        )
    )

    # =======================================================
    # SOC
    # =======================================================

    project_soc_5m = unary_field(
        clean_soc,
        field=Sensor.project_soc_raw_5m,
    )

    bank_soc_5m = unary_field(
        clean_soc,
        field=Sensor.bank_soc_raw_5m,
    )

    block_soc_5m = unary_field(
        clean_soc,
        field=Sensor.block_soc_raw_5m,
    )

    string_soc_5m = unary_field(
        clean_soc,
        field=Sensor.string_soc_raw_5m,
    )

    # =======================================================
    # SOH
    # =======================================================

    bank_soh_5m = unary_field(
        clean_soh,
        field=Sensor.bank_soh_raw_5m,
    )

    string_soh_5m = unary_field(
        clean_soh,
        field=Sensor.string_soh_raw_5m,
    )

    # =======================================================
    # Current
    # =======================================================

    @method_calc(
        current=Required(Sensor.string_current_raw_amps_5m),
    )
    def string_current_amps_5m(
        current: xr.DataArray,
    ) -> xr.DataArray:
        return current.where(
            filter_mask(filter_by=current, min_value=-1000, max_value=1000)
        )

    # =======================================================
    # Temperature
    # =======================================================

    string_avg_cell_temp_c_5m = unary_field(
        clean_temperature,
        field=Sensor.string_avg_cell_temp_raw_c_5m,
    )

    string_min_cell_temp_c_5m = unary_field(
        clean_temperature,
        field=Sensor.string_min_cell_temp_raw_c_5m,
    )

    string_max_cell_temp_c_5m = unary_field(
        clean_temperature,
        field=Sensor.string_max_cell_temp_raw_c_5m,
    )

    string_min_module_temp_c_5m = unary_field(
        clean_temperature,
        field=Sensor.string_min_module_temp_raw_c_5m,
    )

    string_max_module_temp_c_5m = unary_field(
        clean_temperature,
        field=Sensor.string_max_module_temp_raw_c_5m,
    )

    string_avg_module_temp_c_5m = unary_field(
        clean_temperature,
        field=Sensor.string_avg_module_temp_raw_c_5m,
    )

    # =======================================================
    # Voltage
    # =======================================================

    string_avg_cell_voltage_v_5m = unary_field(
        clean_cell_voltage,
        field=Sensor.string_avg_cell_voltage_raw_v_5m,
    )

    string_min_cell_voltage_v_5m = unary_field(
        clean_cell_voltage,
        field=Sensor.string_min_cell_voltage_raw_v_5m,
    )

    string_max_cell_voltage_v_5m = unary_field(
        clean_cell_voltage,
        field=Sensor.string_max_cell_voltage_raw_v_5m,
    )
