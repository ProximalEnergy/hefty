from core.enumerations import SensorType

from kpi_pipeline.base.field import Field
from kpi_pipeline.base.models import SensorModel
from kpi_pipeline.services.schema import DownloadTimeSeriesSchema


class DownloadTimeSeriesDataBESS(DownloadTimeSeriesSchema):
    bess_string_current_amps_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_STRING_CURRENT,
        )
    )

    meter_total_consumed_energy_kwh_5m = Field(
        SensorModel(
            sensor_type=SensorType.METER_CONSUMED_ENERGY,
            project_level=True,
            scale=1000,
        )
    )

    meter_total_delivered_energy_kwh_5m = Field(
        SensorModel(
            sensor_type=SensorType.METER_DELIVERED_ENERGY,
            project_level=True,
            scale=1000,
        )
    )

    project_total_aux_energy_kwh_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_MV_AUX_METER_CONSUMED_ENERGY,
            project_level=True,
            scale=1000,
        )
    )

    bess_string_total_energy_charged_kwh_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_STRING_CHARGE_ENERGY_TOTAL,
            scale=1000,
        ),
    )

    bess_pcs_total_energy_charged_kwh_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_PCS_CHARGE_ENERGY_TOTAL,
            scale=1000,
        ),
    )

    bess_pcs_total_energy_discharged_kwh_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_PCS_DISCHARGE_ENERGY_TOTAL,
            scale=1000,
        ),
    )

    bess_pcs_module_total_energy_discharged_kwh_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_PCS_MODULE_DISCHARGE_ENERGY_TOTAL,
            scale=1000,
        ),
    )

    bess_pcs_module_energy_charged_total_kwh_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_PCS_MODULE_CHARGE_ENERGY_TOTAL,
            scale=1000,
        ),
    )

    bess_string_total_energy_discharged_kwh_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_STRING_DISCHARGE_ENERGY_TOTAL,
            scale=1000,
        ),
    )

    project_power_kw_5m = Field(
        SensorModel(
            sensor_type=SensorType.METER_ACTIVE_POWER,
            project_level=True,
            scale=1000,
        ),
    )

    bess_pcs_power_kw_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_PCS_AC_POWER,
            scale=1000,
        ),
    )

    bess_string_power_kw_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_STRING_POWER,
            scale=1000,
        ),
    )

    # SOC Download

    bess_bank_soc_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_BANK_SOC_PERCENT,
        ),
    )

    bess_block_soc_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_BLOCK_SOC_PERCENT,
        ),
    )

    # removed bess enclosure soc because it doesn't seem to be configured for any projects

    bess_string_soc_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_STRING_SOC_PERCENT,
        ),
    )

    project_soc_5m = Field(
        SensorModel(sensor_type=SensorType.PROJECT_SOC_PERCENT, project_level=True),
    )

    bess_bank_soh_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_BANK_SOH_PERCENT,
        ),
    )

    bess_string_soh_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_STRING_SOH_PERCENT,
        ),
    )

    bess_string_avg_cell_temp_c_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_STRING_AVG_CELL_TEMPERATURE,
        )
    )
    bess_string_min_cell_temp_c_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_STRING_MIN_CELL_TEMPERATURE,
        )
    )
    bess_string_max_cell_temp_c_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_STRING_MAX_CELL_TEMPERATURE,
        )
    )
    bess_string_min_module_temp_c_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_STRING_MIN_MODULE_TEMPERATURE,
        ),
    )

    bess_string_max_module_temp_c_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_STRING_MAX_MODULE_TEMPERATURE,
        ),
    )

    bess_string_avg_module_temp_c_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_STRING_AVG_MODULE_TEMPERATURE,
        ),
    )

    bess_string_avg_cell_voltage_v_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_STRING_AVG_CELL_VOLTAGE,
        )
    )

    bess_string_min_cell_voltage_v_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_STRING_MIN_CELL_VOLTAGE,
        )
    )

    bess_string_max_cell_voltage_v_5m = Field(
        SensorModel(
            sensor_type=SensorType.BESS_STRING_MAX_CELL_VOLTAGE,
        )
    )
