from kpi.domain.bess import (
    clean_cell_voltage,
    clean_power,
    clean_soc,
    clean_soh,
    clean_temperature,
)
from kpi.domain.general import filter_by_value
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.arg import Constant, required
from kpi.op.transform.method import MethodCalc, calc_field
from kpi.registry.download.sensor.bess import DownloadSensorBess as Sensor
from kpi.registry.transform.bess.clean.device_attribute import (
    TransformBessCleanDeviceAttribute as Device,
)
from kpi.registry.transform.bess.clean.project_attribute import (
    TransformBessCleanProjectAttribute as Project,
)


class TransformBessCleanSensor(FieldRegistry[MethodCalc]):
    # =======================================================
    # Power
    # =======================================================

    # project level

    project_power_kw_5m = calc_field(clean_power)(
        power=required(Sensor.project_power_raw_kw_5m),
        capacity=required(Project.project_power_capacity_kw),
    )

    # pcs level

    pcs_power_kw_5m = calc_field(clean_power)(
        power=required(Sensor.pcs_power_raw_kw_5m),
        capacity=required(Device.pcs_power_capacity_kw),
    )

    pcs_available_charge_power_kw_5m = calc_field(filter_by_value)(
        required(Sensor.pcs_available_charge_power_raw_kw_5m),
        min_value=Constant(value=0),
    )

    pcs_available_discharge_power_kw_5m = calc_field(filter_by_value)(
        required(Sensor.pcs_available_discharge_power_raw_kw_5m),
        min_value=Constant(value=0),
    )

    # string
    string_power_kw_5m = calc_field(clean_power)(
        power=required(Sensor.string_power_raw_kw_5m),
        capacity=required(Device.string_power_capacity_kw),
    )

    # =======================================================
    # SOC
    # =======================================================

    project_soc_5m = calc_field(clean_soc)(required(Sensor.project_soc_raw_5m))

    bank_soc_5m = calc_field(clean_soc)(required(Sensor.bank_soc_raw_5m))

    block_soc_5m = calc_field(clean_soc)(required(Sensor.block_soc_raw_5m))

    string_soc_5m = calc_field(clean_soc)(required(Sensor.string_soc_raw_5m))

    # =======================================================
    # SOH
    # =======================================================

    bank_soh_5m = calc_field(clean_soh)(required(Sensor.bank_soh_raw_5m))

    string_soh_5m = calc_field(clean_soh)(required(Sensor.string_soh_raw_5m))

    # =======================================================
    # Current
    # =======================================================

    string_current_amps_5m = calc_field(filter_by_value)(
        required(Sensor.string_current_raw_amps_5m),
        min_value=Constant(value=-1000),
        max_value=Constant(value=1000),
    )

    # =======================================================
    # Temperature
    # =======================================================

    string_avg_cell_temp_c_5m = calc_field(clean_temperature)(
        required(Sensor.string_avg_cell_temp_raw_c_5m)
    )

    string_min_cell_temp_c_5m = calc_field(clean_temperature)(
        required(Sensor.string_min_cell_temp_raw_c_5m)
    )

    string_max_cell_temp_c_5m = calc_field(clean_temperature)(
        required(Sensor.string_max_cell_temp_raw_c_5m)
    )

    string_min_module_temp_c_5m = calc_field(clean_temperature)(
        required(Sensor.string_min_module_temp_raw_c_5m)
    )

    string_max_module_temp_c_5m = calc_field(clean_temperature)(
        required(Sensor.string_max_module_temp_raw_c_5m)
    )

    string_avg_module_temp_c_5m = calc_field(clean_temperature)(
        required(Sensor.string_avg_module_temp_raw_c_5m)
    )

    # =======================================================
    # Voltage
    # =======================================================

    string_avg_cell_voltage_v_5m = calc_field(clean_cell_voltage)(
        required(Sensor.string_avg_cell_voltage_raw_v_5m)
    )

    string_min_cell_voltage_v_5m = calc_field(clean_cell_voltage)(
        required(Sensor.string_min_cell_voltage_raw_v_5m)
    )

    string_max_cell_voltage_v_5m = calc_field(clean_cell_voltage)(
        required(Sensor.string_max_cell_voltage_raw_v_5m)
    )
