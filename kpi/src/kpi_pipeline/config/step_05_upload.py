from core.enumerations import KPIType

from kpi_pipeline.base.models import KPIMetadata
from kpi_pipeline.base.schema import ScopeWrappedAction
from kpi_pipeline.config.step_04_aggregate import Aggregate
from kpi_pipeline.services.action.action import UploadKpiAction

# sorted alphabetically
kpi_map: dict[KPIType, KPIMetadata] = {
    KPIType.BESS_BANK_AVAILABILITY: KPIMetadata(
        project_var=Aggregate.project_bess_bank_availability_d.var,
        device_var=Aggregate.bess_bank_availability_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_BANK_AVERAGE_SOC_PERCENT: KPIMetadata(
        project_var=Aggregate.project_avg_bank_soc_d.var,
        device_var=Aggregate.bess_bank_avg_soc_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_BANK_CYCLE_COUNT: KPIMetadata(
        project_var=Aggregate.project_avg_bank_cycle_count_d.var,
        device_var=Aggregate.bess_bank_cycle_count_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_BANK_DEPTH_OF_DISCHARGE: KPIMetadata(
        project_var=Aggregate.project_avg_bank_dod_d.var,
        device_var=Aggregate.bess_bank_avg_dod_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_BANK_RESTING_SOC_PERCENT: KPIMetadata(
        project_var=Aggregate.project_avg_bank_resting_soc_d.var,
        device_var=Aggregate.bess_bank_avg_resting_soc_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_BANK_SOH: KPIMetadata(
        project_var=Aggregate.project_avg_bank_soh_d.var,
        device_var=Aggregate.bess_bank_avg_soh_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_BLOCK_AVERAGE_SOC_PERCENT: KPIMetadata(
        project_var=Aggregate.project_avg_block_soc_d.var,
        device_var=Aggregate.bess_block_avg_soc_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_BLOCK_CYCLE_COUNT: KPIMetadata(
        project_var=Aggregate.project_avg_block_cycle_count_d.var,
        device_var=Aggregate.bess_block_cycle_count_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_BLOCK_RESTING_SOC_PERCENT: KPIMetadata(
        project_var=Aggregate.project_avg_block_resting_soc_d.var,
        device_var=Aggregate.bess_block_avg_resting_soc_d.var,
        version="1.0.0",
    ),
    # deprecating bess enclosure KPIS
    # - KPIType.BESS_DC_ENCLOSURE_AVERAGE_SOC_PERCENT
    # - KPIType.BESS_DC_ENCLOSURE_CYCLE_COUNT
    # because only sun streams 3 had tags for soc bess enclosures
    KPIType.BESS_DC_ENCLOSURE_AVERAGE_SOC_PERCENT: KPIMetadata(
        project_var=Aggregate.project_avg_string_resting_soc_d.var,
        device_var=Aggregate.bess_enclosure_avg_resting_soc_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_MV_AUX_METER_ENERGY: KPIMetadata(
        project_var=Aggregate.project_energy_aux_meter_kwh_d.var,
        version="1.0.0",
        scale=0.001,
    ),
    KPIType.BESS_PCS_AVAILABILITY: KPIMetadata(
        project_var=Aggregate.project_bess_pcs_availability_d.var,
        device_var=Aggregate.bess_pcs_availability_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_PCS_AVERAGE_C_RATE: KPIMetadata(
        project_var=Aggregate.project_avg_pcs_c_rate_d.var,
        device_var=Aggregate.bess_pcs_avg_c_rate_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_PCS_AVERAGE_C_RATE_WHILE_CHARGING: KPIMetadata(
        project_var=Aggregate.project_avg_pcs_c_rate_while_charging_d.var,
        device_var=Aggregate.bess_pcs_avg_c_rate_charging_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_PCS_AVERAGE_C_RATE_WHILE_DISCHARGING: KPIMetadata(
        project_var=Aggregate.project_avg_pcs_c_rate_while_discharging_d.var,
        device_var=Aggregate.bess_pcs_avg_c_rate_discharging_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_PCS_AVG_REAL_AC_POWER_WHILE_CHARGING: KPIMetadata(
        project_var=Aggregate.project_avg_pcs_power_while_charging_kw_d.var,
        device_var=Aggregate.bess_pcs_avg_power_while_charging_kw_d.var,
        version="1.0.0",
        scale=0.001,
    ),
    KPIType.BESS_PCS_AVG_REAL_AC_POWER_WHILE_DISCHARGING: KPIMetadata(
        project_var=Aggregate.project_avg_pcs_power_while_discharging_kw_d.var,
        device_var=Aggregate.bess_pcs_avg_power_while_discharging_kw_d.var,
        version="1.0.0",
        scale=0.001,
    ),
    KPIType.BESS_PCS_HOURS_CHARGING: KPIMetadata(
        project_var=Aggregate.project_total_pcs_time_charging_hours_d.var,
        device_var=Aggregate.bess_pcs_total_time_charging_hours_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_PCS_HOURS_DISCHARGING: KPIMetadata(
        project_var=Aggregate.project_total_pcs_time_while_discharging_hours_d.var,
        device_var=Aggregate.bess_pcs_total_time_discharging_hours_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_PCS_HOURS_IDLING: KPIMetadata(
        project_var=Aggregate.project_total_pcs_time_idling_hours_d.var,
        device_var=Aggregate.bess_pcs_total_time_idling_hours_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_PCS_MODULE_AVAILABILITY: KPIMetadata(
        project_var=Aggregate.project_bess_pcs_module_availability_d.var,
        device_var=Aggregate.bess_pcs_module_availability_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_PROJECT_AVERAGE_C_RATE_WHILE_CHARGING: KPIMetadata(
        project_var=Aggregate.project_avg_c_rate_while_charging_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_PROJECT_AVERAGE_C_RATE_WHILE_DISCHARGING: KPIMetadata(
        project_var=Aggregate.project_avg_c_rate_while_discharging_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_PROJECT_CHARGE_CYCLES: KPIMetadata(
        project_var=Aggregate.project_cycles_charging_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_PROJECT_DISCHARGE_CYCLES: KPIMetadata(
        project_var=Aggregate.project_cycles_discharging_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_PROJECT_ENERGY_CHARGED: KPIMetadata(
        project_var=Aggregate.project_energy_charged_kwh_d.var,
        version="1.0.0",
        scale=0.001,
    ),
    KPIType.BESS_PROJECT_HOURS_CHARGING: KPIMetadata(
        project_var=Aggregate.project_total_time_charging_hours_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_PROJECT_HOURS_DISCHARGING: KPIMetadata(
        project_var=Aggregate.project_total_time_while_discharging_hours_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_PROJECT_HOURS_IDLING: KPIMetadata(
        project_var=Aggregate.project_total_time_idling_hours_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_AVERAGE_C_RATE: KPIMetadata(
        project_var=Aggregate.project_avg_string_c_rate_d.var,
        device_var=Aggregate.bess_string_avg_c_rate_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_AVERAGE_SOC_PERCENT: KPIMetadata(
        project_var=Aggregate.project_avg_string_soc_d.var,
        device_var=Aggregate.bess_string_avg_soc_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_AVG_C_RATE_WHILE_CHARGING: KPIMetadata(
        project_var=Aggregate.project_avg_string_c_rate_while_charging_d.var,
        device_var=Aggregate.bess_string_avg_c_rate_while_charging_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_AVG_C_RATE_WHILE_DISCHARGING: KPIMetadata(
        project_var=Aggregate.project_avg_string_c_rate_while_discharging_d.var,
        device_var=Aggregate.bess_string_avg_c_rate_while_discharging_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_AVG_CELL_TEMPERATURE: KPIMetadata(
        project_var=Aggregate.project_avg_string_cell_temp_c_d.var,
        device_var=Aggregate.bess_string_avg_cell_temp_c_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_AVG_CELL_VOLTAGE: KPIMetadata(
        project_var=Aggregate.project_avg_string_cell_voltage_v_d.var,
        device_var=Aggregate.bess_string_avg_cell_voltage_v_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_AVG_CURRENT: KPIMetadata(
        project_var=Aggregate.project_avg_string_current_amps_d.var,
        device_var=Aggregate.bess_string_avg_current_amps_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_AVG_CURRENT_WHILE_CHARGING: KPIMetadata(
        project_var=Aggregate.project_avg_string_current_while_charging_amps_d.var,
        device_var=Aggregate.bess_string_avg_current_while_charging_amps_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_AVG_CURRENT_WHILE_DISCHARGING: KPIMetadata(
        project_var=Aggregate.project_avg_string_current_while_discharging_amps_d.var,
        device_var=Aggregate.bess_string_avg_current_while_discharging_amps_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_AVG_MODULE_TEMP: KPIMetadata(
        project_var=Aggregate.project_avg_string_module_temp_c_d.var,
        device_var=Aggregate.bess_string_avg_module_temp_c_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_CYCLE_COUNT: KPIMetadata(
        project_var=Aggregate.project_avg_string_cycle_count_d.var,
        device_var=Aggregate.bess_string_cycle_count_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_DEGRADATION: KPIMetadata(
        project_var=Aggregate.project_total_string_degradation_d.var,
        device_var=Aggregate.bess_string_total_degradation_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_DEPTH_OF_DISCHARGE: KPIMetadata(
        project_var=Aggregate.project_avg_string_dod_d.var,
        device_var=Aggregate.bess_string_avg_dod_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_ENERGY_CHARGED: KPIMetadata(
        project_var=Aggregate.project_energy_charged_string_kwh_d.var,
        device_var=Aggregate.bess_string_energy_charged_kwh_d.var,
        version="1.0.0",
        scale=0.001,
    ),
    KPIType.BESS_STRING_ENERGY_DISCHARGED: KPIMetadata(
        project_var=Aggregate.project_energy_discharged_string_kwh_d.var,
        device_var=Aggregate.bess_string_energy_discharged_kwh_d.var,
        version="1.0.0",
        scale=0.001,
    ),
    KPIType.BESS_STRING_MAX_CELL_TEMPERATURE: KPIMetadata(
        project_var=Aggregate.project_max_string_cell_temp_c_d.var,
        device_var=Aggregate.bess_string_max_cell_temp_c_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_MAX_CELL_VOLTAGE: KPIMetadata(
        project_var=Aggregate.project_max_string_cell_voltage_v_d.var,
        device_var=Aggregate.bess_string_max_cell_voltage_v_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_MAX_CURRENT: KPIMetadata(
        project_var=Aggregate.project_max_string_current_amps_d.var,
        device_var=Aggregate.bess_string_max_current_amps_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_MAX_MODULE_TEMP: KPIMetadata(
        project_var=Aggregate.project_max_string_module_temp_c_d.var,
        device_var=Aggregate.bess_string_max_module_temp_c_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_MIN_CELL_TEMPERATURE: KPIMetadata(
        project_var=Aggregate.project_min_string_cell_temp_c_d.var,
        device_var=Aggregate.bess_string_min_cell_temp_c_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_MIN_CELL_VOLTAGE: KPIMetadata(
        project_var=Aggregate.project_min_string_cell_voltage_v_d.var,
        device_var=Aggregate.bess_string_min_cell_voltage_v_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_MIN_CURRENT: KPIMetadata(
        project_var=Aggregate.project_min_string_current_amps_d.var,
        device_var=Aggregate.bess_string_min_current_amps_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_MIN_MODULE_TEMP: KPIMetadata(
        project_var=Aggregate.project_min_string_module_temp_c_d.var,
        device_var=Aggregate.bess_string_min_module_temp_c_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_RESTING_SOC_PERCENT: KPIMetadata(
        project_var=Aggregate.project_avg_string_resting_soc_d.var,
        device_var=Aggregate.bess_string_avg_resting_soc_d.var,
        version="1.0.0",
    ),
    KPIType.BESS_STRING_SOH: KPIMetadata(
        project_var=Aggregate.project_avg_string_soh_d.var,
        device_var=Aggregate.bess_string_avg_soh_d.var,
        version="1.0.0",
    ),
    KPIType.C_RATE: KPIMetadata(
        project_var=Aggregate.project_avg_c_rate_d.var,
        version="1.0.0",
    ),
    KPIType.MODULE_STATE_OF_HEALTH_BY_COMBINER: KPIMetadata(
        project_var=Aggregate.project_module_excess_degradation_d.var,
        device_var=Aggregate.pv_dc_combiner_module_excess_degradation_d.var,
        version="1.0.0",
    ),
    KPIType.PERFORMANCE_RATIO: KPIMetadata(
        project_var=Aggregate.project_performance_ratio_d.var,
        version="1.0.0",
    ),
    KPIType.PROJECT_AVERAGE_DOD: KPIMetadata(
        project_var=Aggregate.project_avg_dod_d.var,
        version="1.0.0",
    ),
    KPIType.PROJECT_AVERAGE_SOC_PERCENT: KPIMetadata(
        project_var=Aggregate.project_avg_soc_d.var,
        version="1.0.0",
    ),
    KPIType.PROJECT_CYCLE_COUNT: KPIMetadata(
        project_var=Aggregate.project_cycle_count_d.var,
        version="1.0.0",
    ),
    KPIType.PROJECT_ENERGY_DISCHARGED: KPIMetadata(
        project_var=Aggregate.project_energy_discharged_kwh_d.var,
        version="1.0.0",
        scale=0.001,
    ),
    KPIType.PROJECT_ENERGY_PRODUCTION: KPIMetadata(
        project_var=Aggregate.project_energy_production_kwh_d.var,
        version="1.0.0",
        scale=0.001,
    ),
    KPIType.PROJECT_MAXIMUM_CONTINUOUS_DISCHARGED_ENERGY: KPIMetadata(
        project_var=Aggregate.project_maximum_continuous_discharge_kwh_d.var,
        version="1.0.0",
        scale=0.001,
    ),
    KPIType.PROJECT_RESTING_SOC_PERCENT: KPIMetadata(
        project_var=Aggregate.project_avg_resting_soc_d.var,
        version="1.0.0",
    ),
    KPIType.PV_DC_COMBINER_MECHANICAL_AVAILABILITY: KPIMetadata(
        project_var=Aggregate.project_combiner_mechanical_availability_d.var,
        device_var=Aggregate.pv_dc_combiner_mechanical_availability_d.var,
        version="1.0.0",
    ),
    KPIType.PV_DC_COMBINER_FIELD_HEALTH: KPIMetadata(
        project_var=Aggregate.project_avg_pv_dc_combiner_field_health_d.var,
        device_var=Aggregate.pv_dc_combiner_field_health_d.var,
        version="1.0.0",
    ),
    KPIType.PV_PCS_ENERGY_PRODUCTION: KPIMetadata(
        project_var=Aggregate.project_energy_production_pcs_kwh_d.var,
        device_var=Aggregate.pv_pcs_energy_production_kwh_d.var,
        version="1.0.0",
        scale=0.001,
    ),
    KPIType.PV_PCS_MECHANICAL_AVAILABILITY: KPIMetadata(
        project_var=Aggregate.project_mechanical_availability_pcs_d.var,
        device_var=Aggregate.pv_pcs_mechanical_availability_d.var,
        version="1.0.0",
    ),
    KPIType.PV_INVERTER_MODULE_ENERGY_PRODUCTION: KPIMetadata(
        project_var=Aggregate.project_energy_from_pcs_module_kwh_d.var,
        device_var=Aggregate.pv_inverter_module_energy_kwh_d.var,
        version="1.0.0",
        scale=0.001,
    ),
    KPIType.PV_PROJECT_CURTAILMENT: KPIMetadata(
        project_var=Aggregate.project_energy_curtailed_kwh_d.var,
        version="1.0.0",
        scale=0.001,
    ),
    KPIType.PV_PROJECT_EXPECTED_ENERGY_DELIVERED: KPIMetadata(
        project_var=Aggregate.project_energy_expected_best_kwh_d.var,
        version="1.0.0",
        scale=0.001,
    ),
    KPIType.PV_PROJECT_PERFORMANCE_INDEX: KPIMetadata(
        project_var=Aggregate.project_performance_index_d.var,
        version="1.0.0",
    ),
    KPIType.PV_PROJECT_SOLV_CONTRACTUAL_AVAILABILITY: KPIMetadata(
        project_var=Aggregate.project_solv_guarantee_availability_d.var,
        version="1.0.0",
    ),
    KPIType.PV_PROJECT_SOLV_PERIOD_MWH_PRODUCED: KPIMetadata(
        project_var=Aggregate.project_solv_period_kwh_produced_d.var,
        version="1.0.0",
        scale=0.001,
    ),
    KPIType.PV_PROJECT_SOLV_PERIOD_MWH_LOST: KPIMetadata(
        project_var=Aggregate.project_solv_period_kwh_lost_d.var,
        version="1.0.0",
        scale=0.001,
    ),
    KPIType.SPECIFIC_YIELD: KPIMetadata(
        project_var=Aggregate.project_specific_yield_d.var,
        version="1.0.0",
    ),
    KPIType.SUNGROW_BESS_TECHNICAL_AVAILABILITY_GUARANTEE: KPIMetadata(
        project_var=Aggregate.project_complete_availability_d.var,
        device_var=Aggregate.bess_string_complete_availability_d.var,
        version="1.0.0",
    ),
    KPIType.TRACKER_AVAILABILITY_BY_BLOCK: KPIMetadata(
        project_var=Aggregate.project_tracker_availability_d.var,
        device_var=Aggregate.block_tracker_availability_d.var,
        version="1.0.0",
    ),
    KPIType.TRACKER_AVAILABILITY_BY_ROW: KPIMetadata(
        project_var=Aggregate.project_tracker_availability_d.var,
        device_var=Aggregate.tracker_row_availability_d.var,
        version="1.0.0",
    ),
    KPIType.TRACKER_POSITION_DEVIATING_FROM_SETPOINT_BY_BLOCK: KPIMetadata(
        project_var=Aggregate.project_tracker_row_deviation_from_setpoint_deg_d.var,
        device_var=Aggregate.block_tracker_deviation_from_setpoint_deg_d.var,
        version="1.0.0",
    ),
    KPIType.TRACKER_POSITION_DEVIATING_FROM_SETPOINT_BY_ROW: KPIMetadata(
        project_var=Aggregate.project_tracker_row_deviation_from_setpoint_deg_d.var,
        device_var=Aggregate.tracker_row_deviation_from_setpoint_deg_d.var,
        version="1.0.0",
    ),
    KPIType.TRACKER_SETPOINT_DEVIATING_FROM_MEDIAN_BY_BLOCK: KPIMetadata(
        project_var=Aggregate.project_tracker_row_setpoint_deviation_from_median_deg_d.var,
        device_var=Aggregate.block_tracker_setpoint_deviation_from_median_deg_d.var,
        version="1.0.0",
    ),
    KPIType.TRACKER_SETPOINT_DEVIATING_FROM_MEDIAN_BY_ROW: KPIMetadata(
        project_var=Aggregate.project_tracker_row_setpoint_deviation_from_median_deg_d.var,
        device_var=Aggregate.tracker_row_setpoint_deviation_from_median_deg_d.var,
        version="1.0.0",
    ),
}


kpi_upload_action = ScopeWrappedAction(
    transform=UploadKpiAction(kpi_fields=kpi_map), scope="upload_kpi_action"
)
