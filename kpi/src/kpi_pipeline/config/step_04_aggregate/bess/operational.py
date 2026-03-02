from core.enumerations import DeviceType

import kpi_pipeline.services.calc as calc
from kpi_pipeline.base.enums import Aggregation
from kpi_pipeline.base.field import Field
from kpi_pipeline.config.helper_fields import (
    _5min_to_daily,
    _aggregate,
    _device_aggregate,
    _resample_groupby,
)
from kpi_pipeline.config.step_02_validate import Validate
from kpi_pipeline.config.step_03_calculate import Calculate
from kpi_pipeline.services.schema import AddCalculationsSchema


class AggregateBESSOperational(AddCalculationsSchema):
    # ============================================================================
    # C-Rate Calculations
    # ============================================================================
    # Aggregates C-rate (charge/discharge rate relative to capacity) from 5-minute
    # to daily, including overall averages and averages during charging/discharging

    project_avg_pcs_c_rate_d = _aggregate(
        var=Calculate.bess_pcs_c_rate_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_PCS,
    )
    bess_pcs_avg_c_rate_d = _aggregate(
        var=Calculate.bess_pcs_c_rate_5m.var,
        agg=Aggregation.MEAN,
    )

    project_avg_c_rate_d = _aggregate(
        var=Calculate.project_c_rate_5m.var,
        agg=Aggregation.MEAN,
    )

    project_avg_pcs_c_rate_while_charging_d = _aggregate(
        var=Calculate.bess_pcs_c_rate_charging_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_PCS,
    )
    bess_pcs_avg_c_rate_charging_d = _aggregate(
        var=Calculate.bess_pcs_c_rate_charging_5m.var,
        agg=Aggregation.MEAN,
    )

    project_avg_c_rate_while_charging_d = _aggregate(
        var=Calculate.project_c_rate_charging_5m.var,
        agg=Aggregation.MEAN,
    )

    project_avg_pcs_c_rate_while_discharging_d = _aggregate(
        var=Calculate.bess_pcs_c_rate_discharging_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_PCS,
    )
    bess_pcs_avg_c_rate_discharging_d = _aggregate(
        var=Calculate.bess_pcs_c_rate_discharging_5m.var,
        agg=Aggregation.MEAN,
    )

    project_avg_c_rate_while_discharging_d = _aggregate(
        var=Calculate.project_c_rate_discharging_5m.var,
        agg=Aggregation.MEAN,
    )

    # ============================================================================
    # String Current Calculations
    # ============================================================================
    # Aggregates string current from 5-minute to daily, including averages, min/max,
    # and averages during charging/discharging periods

    bess_string_avg_current_amps_d = _aggregate(
        var=Validate.bess_string_current_amps_5m.var,
        agg=Aggregation.MEAN,
    )
    project_avg_string_current_amps_d = _aggregate(
        var=Validate.bess_string_current_amps_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_STRING,
    )

    bess_string_max_current_amps_d = _aggregate(
        var=Validate.bess_string_current_amps_5m.var,
        agg=Aggregation.MAX,
    )
    project_max_string_current_amps_d = _aggregate(
        var=Validate.bess_string_current_amps_5m.var,
        agg=Aggregation.MAX,
        child_device_axis=DeviceType.BESS_STRING,
    )

    bess_string_min_current_amps_d = _aggregate(
        var=Validate.bess_string_current_amps_5m.var,
        agg=Aggregation.MIN,
    )
    project_min_string_current_amps_d = _aggregate(
        var=Validate.bess_string_current_amps_5m.var,
        agg=Aggregation.MIN,
        child_device_axis=DeviceType.BESS_STRING,
    )

    bess_string_avg_current_while_charging_amps_d = Field(
        calc.AverageWhileChargingCalc(
            x_var=Validate.bess_string_current_amps_5m.var,
            c_rate_var=Calculate.bess_string_c_rate_5m.var,
            combiner_model=_5min_to_daily(),
        )
    )

    project_avg_string_current_while_charging_amps_d = Field(
        calc.AverageWhileChargingCalc(
            x_var=Validate.bess_string_current_amps_5m.var,
            c_rate_var=Calculate.bess_string_c_rate_5m.var,
            combiner_model=_5min_to_daily(
                child_device_axis=DeviceType.BESS_STRING,
            ),
        )
    )

    bess_string_avg_current_while_discharging_amps_d = Field(
        calc.AverageWhileDischargingCalc(
            x_var=Validate.bess_string_current_amps_5m.var,
            c_rate_var=Calculate.bess_string_c_rate_5m.var,
            combiner_model=_5min_to_daily(),
        )
    )
    project_avg_string_current_while_discharging_amps_d = Field(
        calc.AverageWhileDischargingCalc(
            x_var=Validate.bess_string_current_amps_5m.var,
            c_rate_var=Calculate.bess_string_c_rate_5m.var,
            combiner_model=_5min_to_daily(
                child_device_axis=DeviceType.BESS_STRING,
            ),
        )
    )

    # ============================================================================
    # Cycle Calculations
    # ============================================================================
    # Calculates charging/discharging cycles and cycle counts from SOC data
    # aggregated from 5-minute to daily

    project_cycles_charging_d = Field(
        calc.ChargingCyclesFromSocCalc(
            soc_5m_var=Validate.project_soc_5m.var,
            time_combiner_model=_5min_to_daily(),
        )
    )

    project_cycles_discharging_d = Field(
        calc.DischargingCyclesFromSocCalc(
            soc_5m_var=Validate.project_soc_5m.var,
            time_combiner_model=_5min_to_daily(),
        )
    )

    bess_bank_cycle_count_d = Field(
        calc.CycleCountFromSocCalc(
            soc_5m_var=Validate.bess_bank_soc_5m.var,
            time_combiner_model=_5min_to_daily(),
        )
    )

    bess_block_cycle_count_d = Field(
        calc.CycleCountFromSocCalc(
            soc_5m_var=Validate.bess_block_soc_5m.var,
            time_combiner_model=_5min_to_daily(),
        )
    )

    bess_string_cycle_count_d = Field(
        calc.CycleCountFromSocCalc(
            soc_5m_var=Validate.bess_string_soc_5m.var,
            time_combiner_model=_5min_to_daily(),
        )
    )

    project_cycle_count_d = Field(
        calc.CycleCountFromSocCalc(
            soc_5m_var=Validate.project_soc_5m.var,
            time_combiner_model=_5min_to_daily(),
        )
    )

    project_avg_bank_cycle_count_d = _device_aggregate(
        var=bess_bank_cycle_count_d.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_BANK,
    )

    project_avg_block_cycle_count_d = _device_aggregate(
        var=bess_block_cycle_count_d.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_BLOCK,
    )

    project_avg_string_cycle_count_d = _device_aggregate(
        var=bess_string_cycle_count_d.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_STRING,
    )

    # ============================================================================
    # Power Calculations (While Charging/Discharging)
    # ============================================================================
    # Calculates average power during charging and discharging periods

    bess_pcs_avg_power_while_charging_kw_d = Field(
        calc.AverageWhileChargingCalc(
            x_var=Validate.bess_pcs_power_kw_5m.var,
            c_rate_var=Calculate.bess_pcs_c_rate_5m.var,
            combiner_model=_5min_to_daily(),
        )
    )
    project_avg_pcs_power_while_charging_kw_d = Field(
        calc.AverageWhileChargingCalc(
            x_var=Validate.bess_pcs_power_kw_5m.var,
            c_rate_var=Calculate.bess_pcs_c_rate_5m.var,
            combiner_model=_5min_to_daily(
                child_device_axis=DeviceType.BESS_PCS,
            ),
        )
    )

    bess_pcs_avg_power_while_discharging_kw_d = Field(
        calc.AverageWhileDischargingCalc(
            x_var=Validate.bess_pcs_power_kw_5m.var,
            c_rate_var=Calculate.bess_pcs_c_rate_5m.var,
            combiner_model=_5min_to_daily(),
        )
    )
    project_avg_pcs_power_while_discharging_kw_d = Field(
        calc.AverageWhileDischargingCalc(
            x_var=Validate.bess_pcs_power_kw_5m.var,
            c_rate_var=Calculate.bess_pcs_c_rate_5m.var,
            combiner_model=_5min_to_daily(
                child_device_axis=DeviceType.BESS_PCS,
            ),
        )
    )

    # ============================================================================
    # Time Aggregations
    # ============================================================================
    # Aggregates time spent in different operational states (charging, discharging,
    # idling) and calculates portion of time in each state

    project_total_pcs_time_charging_hours_d = _resample_groupby(
        field=Calculate.bess_pcs_time_charging_hours_5m.var,
        agg_resample=Aggregation.SUM,
        agg_groupby=Aggregation.MEAN,
        from_device_axis=DeviceType.BESS_PCS,
    )
    bess_pcs_total_time_charging_hours_d = _aggregate(
        var=Calculate.bess_pcs_time_charging_hours_5m.var,
        agg=Aggregation.SUM,
    )

    project_total_time_charging_hours_d = _aggregate(
        var=Calculate.project_time_charging_hours_5m.var,
        agg=Aggregation.SUM,
    )

    project_total_pcs_time_while_discharging_hours_d = _resample_groupby(
        field=Calculate.bess_pcs_time_discharging_hours_5m.var,
        agg_resample=Aggregation.SUM,
        agg_groupby=Aggregation.MEAN,
        from_device_axis=DeviceType.BESS_PCS,
    )
    bess_pcs_total_time_discharging_hours_d = _aggregate(
        var=Calculate.bess_pcs_time_discharging_hours_5m.var,
        agg=Aggregation.SUM,
    )

    project_total_time_while_discharging_hours_d = _aggregate(
        var=Calculate.project_time_discharging_hours_5m.var,
        agg=Aggregation.SUM,
    )

    project_total_pcs_time_idling_hours_d = _resample_groupby(
        field=Calculate.bess_pcs_time_idling_hours_5m.var,
        agg_resample=Aggregation.SUM,
        agg_groupby=Aggregation.MEAN,
        from_device_axis=DeviceType.BESS_PCS,
    )
    bess_pcs_total_time_idling_hours_d = _aggregate(
        var=Calculate.bess_pcs_time_idling_hours_5m.var,
        agg=Aggregation.SUM,
    )

    project_total_time_idling_hours_d = _aggregate(
        var=Calculate.project_time_idling_hours_5m.var,
        agg=Aggregation.SUM,
    )

    project_portion_of_time_charging_d = _aggregate(
        var=Calculate.project_is_charging_5m.var,
        agg=Aggregation.MEAN,
    )

    project_portion_of_time_discharging_d = _aggregate(
        var=Calculate.project_is_discharging_5m.var,
        agg=Aggregation.MEAN,
    )

    project_portion_of_time_idling_d = _aggregate(
        var=Calculate.project_is_idling_5m.var,
        agg=Aggregation.MEAN,
    )
