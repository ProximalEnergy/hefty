from core.enumerations import SensorType
from kpi.base.protocol import SensorProtocol
from kpi.op.download.sensor import sensor_field
from kpi.op.field_registry import FieldRegistry


class DownloadSensorBess(FieldRegistry[SensorProtocol]):
    # =======================================================
    # Energy
    # =======================================================

    # project level

    project_total_energy_charged_raw_kwh_5m = sensor_field(
        sensor_type=SensorType.METER_CONSUMED_ENERGY,
        project_level=True,
        scale=1000,
    )

    project_total_energy_discharged_raw_kwh_5m = sensor_field(
        sensor_type=SensorType.METER_DELIVERED_ENERGY,
        project_level=True,
        scale=1000,
    )

    project_total_aux_energy_raw_kwh_5m = sensor_field(
        sensor_type=SensorType.BESS_MV_AUX_METER_CONSUMED_ENERGY,
        project_level=True,
        scale=1000,
    )

    # mv circuit level

    circuit_total_energy_charged_raw_kwh_5m = sensor_field(
        sensor_type=SensorType.BESS_MV_COLLECTOR_CIRCUIT_METER_CONSUMED_ENERGY,
        scale=1000,
    )

    circuit_total_energy_discharged_raw_kwh_5m = sensor_field(
        sensor_type=SensorType.BESS_MV_COLLECTOR_CIRCUIT_METER_DELIVERED_ENERGY,
        scale=1000,
    )

    # pcs level

    pcs_total_energy_charged_raw_kwh_5m = sensor_field(
        sensor_type=SensorType.BESS_PCS_CHARGE_ENERGY_TOTAL,
        scale=1000,
    )

    pcs_total_energy_discharged_raw_kwh_5m = sensor_field(
        sensor_type=SensorType.BESS_PCS_DISCHARGE_ENERGY_TOTAL,
        scale=1000,
    )

    # pcs module level

    pcs_module_total_energy_discharged_raw_kwh_5m = sensor_field(
        sensor_type=SensorType.BESS_PCS_MODULE_DISCHARGE_ENERGY_TOTAL,
        scale=1000,
    )

    pcs_module_total_energy_charged_raw_kwh_5m = sensor_field(
        sensor_type=SensorType.BESS_PCS_MODULE_CHARGE_ENERGY_TOTAL,
        scale=1000,
    )

    # string level

    string_total_energy_charged_raw_kwh_5m = sensor_field(
        sensor_type=SensorType.BESS_STRING_CHARGE_ENERGY_TOTAL,
        scale=1000,
    )

    string_total_energy_discharged_raw_kwh_5m = sensor_field(
        sensor_type=SensorType.BESS_STRING_DISCHARGE_ENERGY_TOTAL,
        scale=1000,
    )

    # =======================================================
    # Power
    # =======================================================

    # project level

    project_power_raw_kw_5m = sensor_field(
        sensor_type=SensorType.METER_ACTIVE_POWER,
        project_level=True,
        scale=1000,
    )

    # pcs level

    pcs_power_raw_kw_5m = sensor_field(
        sensor_type=SensorType.BESS_PCS_AC_POWER,
        scale=1000,
    )

    # string

    string_power_raw_kw_5m = sensor_field(
        sensor_type=SensorType.BESS_STRING_POWER,
        scale=1000,
    )

    # =======================================================
    # SOC
    # =======================================================

    project_soc_raw_5m = sensor_field(
        sensor_type=SensorType.PROJECT_SOC_PERCENT,
        project_level=True,
    )

    bank_soc_raw_5m = sensor_field(
        sensor_type=SensorType.BESS_BANK_SOC_PERCENT,
    )

    block_soc_raw_5m = sensor_field(
        sensor_type=SensorType.BESS_BLOCK_SOC_PERCENT,
    )

    string_soc_raw_5m = sensor_field(
        sensor_type=SensorType.BESS_STRING_SOC_PERCENT,
    )

    # =======================================================
    # SOH
    # =======================================================

    bank_soh_raw_5m = sensor_field(
        sensor_type=SensorType.BESS_BANK_SOH_PERCENT,
    )

    string_soh_raw_5m = sensor_field(
        sensor_type=SensorType.BESS_STRING_SOH_PERCENT,
    )

    # =======================================================
    # Current
    # =======================================================

    string_current_raw_amps_5m = sensor_field(
        sensor_type=SensorType.BESS_STRING_CURRENT,
    )

    # =======================================================
    # Temperature
    # =======================================================

    string_avg_cell_temp_raw_c_5m = sensor_field(
        sensor_type=SensorType.BESS_STRING_AVG_CELL_TEMPERATURE,
    )
    string_min_cell_temp_raw_c_5m = sensor_field(
        sensor_type=SensorType.BESS_STRING_MIN_CELL_TEMPERATURE,
    )
    string_max_cell_temp_raw_c_5m = sensor_field(
        sensor_type=SensorType.BESS_STRING_MAX_CELL_TEMPERATURE,
    )
    string_min_module_temp_raw_c_5m = sensor_field(
        sensor_type=SensorType.BESS_STRING_MIN_MODULE_TEMPERATURE,
    )

    string_max_module_temp_raw_c_5m = sensor_field(
        sensor_type=SensorType.BESS_STRING_MAX_MODULE_TEMPERATURE,
    )

    string_avg_module_temp_raw_c_5m = sensor_field(
        sensor_type=SensorType.BESS_STRING_AVG_MODULE_TEMPERATURE,
    )

    # =======================================================
    # Voltage
    # =======================================================

    string_avg_cell_voltage_raw_v_5m = sensor_field(
        sensor_type=SensorType.BESS_STRING_AVG_CELL_VOLTAGE,
    )

    string_min_cell_voltage_raw_v_5m = sensor_field(
        sensor_type=SensorType.BESS_STRING_MIN_CELL_VOLTAGE,
    )

    string_max_cell_voltage_raw_v_5m = sensor_field(
        sensor_type=SensorType.BESS_STRING_MAX_CELL_VOLTAGE,
    )
