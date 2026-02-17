from core.enumerations import SensorType

from kpi_pipeline.base.enums import Aggregation
from kpi_pipeline.base.field import Field
from kpi_pipeline.base.models import SensorModel
from kpi_pipeline.services.schema import DownloadTimeSeriesSchema


class DownloadTimeSeriesPV(DownloadTimeSeriesSchema):
    project_active_power_meter_kw_5m = Field(
        SensorModel(
            sensor_type=SensorType.METER_ACTIVE_POWER,
            project_level=True,
            scale=1000,
        )
    )

    # pcs

    pv_pcs_active_power_ac_kw_5m = Field(
        SensorModel(
            sensor_type=SensorType.PV_PCS_AC_POWER,
            scale=1000,
        )
    )

    pv_pcs_reactive_power_kvar_5m = Field(
        SensorModel(
            sensor_type=SensorType.PV_PCS_REACTIVE_POWER,
            scale=1000,
        )
    )

    pv_pcs_active_power_setpoint_kw_5m = Field(
        SensorModel(
            sensor_type=SensorType.PV_PCS_AC_POWER_SETPOINT,
            scale=1000,
        )
    )

    pv_pcs_voltage_v_5m = Field(
        SensorModel(
            sensor_type=SensorType.PV_PCS_DC_VOLTAGE,
        )
    )

    pv_dc_combiner_current_amps_5m = Field(
        SensorModel(
            sensor_type=SensorType.PV_DC_COMBINER_CURRENT,
        )
    )

    pv_pcs_energy_production_total_kwh_5m = Field(
        SensorModel(
            sensor_type=SensorType.PV_PCS_AC_NET_ENERGY,
            scale=1000,
        )
    )

    # pv pcs module

    pv_pcs_module_power_ac_kw_5m = Field(
        SensorModel(
            sensor_type=SensorType.PV_PCS_MODULE_AC_POWER,
            scale=1000,
        )
    )

    pv_pcs_module_voltage_v_5m = Field(
        SensorModel(
            sensor_type=SensorType.PV_PCS_MODULE_DC_VOLTAGE,
        )
    )

    project_power_setpoint_kw_5m = Field(
        SensorModel(
            sensor_type=SensorType.PPC_ACTIVE_POWER_SETPOINT,
            project_level=True,
        )
    )

    met_station_irradiance_poa_w_m2_5m = Field(
        SensorModel(sensor_type=SensorType.MET_STATION_POA, aggregation=Aggregation.MAX)
    )

    tracker_row_position_deg_5m = Field(
        SensorModel(
            sensor_type=SensorType.TRACKER_POSITION,
        )
    )

    tracker_row_setpoint_deg_5m = Field(
        SensorModel(
            sensor_type=SensorType.TRACKER_SETPOINT,
        )
    )
