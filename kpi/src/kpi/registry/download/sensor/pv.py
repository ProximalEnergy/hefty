from core.enumerations import SensorTypeEnum

from kpi.base.protocol import SensorProtocol
from kpi.op.download.sensor import SensorMax, sensor_field
from kpi.op.field import Field
from kpi.op.field_registry import FieldRegistry


class DownloadSensorPv(FieldRegistry[SensorProtocol]):
    project_total_energy_exported_to_grid_raw_kwh_5m = sensor_field(
        sensor_type=SensorTypeEnum.METER_ENERGY_EXPORTED_TO_GRID,
        project_level=True,
        scale=1000,
    )

    # pcs

    inverter_ac_power_raw_kw_5m = sensor_field(
        sensor_type=SensorTypeEnum.PV_INVERTER_AC_POWER,
        scale=1000,
    )

    inverter_reactive_power_raw_kvar_5m = sensor_field(
        sensor_type=SensorTypeEnum.PV_INVERTER_REACTIVE_POWER,
        scale=1000,
    )

    inverter_ac_power_setpoint_raw_kw_5m = sensor_field(
        sensor_type=SensorTypeEnum.PV_INVERTER_AC_POWER_SETPOINT,
        scale=1000,
    )

    inverter_voltage_raw_v_5m = sensor_field(
        sensor_type=SensorTypeEnum.PV_INVERTER_DC_VOLTAGE,
    )

    combiner_current_raw_amps_5m = sensor_field(
        sensor_type=SensorTypeEnum.PV_DC_COMBINER_CURRENT,
    )

    inverter_total_energy_production_raw_kwh_5m = sensor_field(
        sensor_type=SensorTypeEnum.PV_INVERTER_AC_NET_ENERGY,
        scale=1000,
    )

    # pv inverter module

    inverter_module_ac_power_raw_kw_5m = sensor_field(
        sensor_type=SensorTypeEnum.PV_INVERTER_MODULE_AC_POWER,
        scale=1000,
    )

    inverter_module_voltage_raw_v_5m = sensor_field(
        sensor_type=SensorTypeEnum.PV_INVERTER_MODULE_DC_VOLTAGE,
    )

    project_power_setpoint_raw_kw_5m = sensor_field(
        sensor_type=SensorTypeEnum.PPC_ACTIVE_POWER_SETPOINT,
        project_level=True,
        scale=1000,
    )

    met_poa_irradiance_raw_w_m2_5m = Field[SensorProtocol](
        SensorMax(sensor_type=SensorTypeEnum.MET_STATION_POA)
    )

    tracker_row_position_raw_deg_5m = sensor_field(
        sensor_type=SensorTypeEnum.TRACKER_ROW_POSITION,
    )

    tracker_row_setpoint_raw_deg_5m = sensor_field(
        sensor_type=SensorTypeEnum.TRACKER_ROW_SETPOINT,
    )
