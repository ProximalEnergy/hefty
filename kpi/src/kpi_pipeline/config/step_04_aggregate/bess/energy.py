from core.enumerations import DeviceType

import kpi_pipeline.services.calc as calc
from kpi_pipeline.base.enums import Aggregation, Time
from kpi_pipeline.base.field import Field
from kpi_pipeline.config.helper_fields import (
    _5min_to_daily,
    _agg_first,
    _device_aggregate,
)
from kpi_pipeline.config.step_01_download import Download
from kpi_pipeline.config.step_02_validate import Validate
from kpi_pipeline.config.step_03_calculate import Calculate
from kpi_pipeline.services.schema import AddCalculationsSchema


class AggregateBESSEnergy(AddCalculationsSchema):
    # ============================================================================
    # Energy Aggregations
    # ============================================================================
    # Aggregates energy metrics from 5-minute to daily by summing or accumulating
    # energy charged, discharged, and auxiliary energy consumption

    #################
    # Get first value
    ##################

    # meter

    meter_total_delivered_energy_kwh_d = _agg_first(
        var=Download.time_series.meter_total_delivered_energy_kwh_5m.var,
    )

    meter_total_consumed_energy_kwh_d = _agg_first(
        var=Download.time_series.meter_total_consumed_energy_kwh_5m.var,
    )

    # aux

    project_total_aux_energy_kwh_d = _agg_first(
        var=Download.time_series.project_total_aux_energy_kwh_5m.var,
    )

    # circuit

    bess_circuit_total_energy_charged_kwh_d = _agg_first(
        var=Download.time_series.bess_circuit_total_energy_charged_kwh_5m.var,
    )
    bess_circuit_total_energy_discharged_kwh_d = _agg_first(
        var=Download.time_series.bess_circuit_total_energy_discharged_kwh_5m.var,
    )

    # pcs

    bess_pcs_total_energy_charged_kwh_d = _agg_first(
        var=Download.time_series.bess_pcs_total_energy_charged_kwh_5m.var,
    )
    bess_pcs_total_energy_discharged_kwh_d = _agg_first(
        var=Download.time_series.bess_pcs_total_energy_discharged_kwh_5m.var,
    )

    # pcs module

    bess_pcs_module_total_energy_charged_kwh_d = _agg_first(
        var=Download.time_series.bess_pcs_module_total_energy_charged_kwh_5m.var,
    )

    bess_pcs_module_total_energy_discharged_kwh_d = _agg_first(
        var=Download.time_series.bess_pcs_module_total_energy_discharged_kwh_5m.var,
    )

    # string

    bess_string_total_energy_charged_kwh_d = _agg_first(
        var=Download.time_series.bess_string_total_energy_charged_kwh_5m.var,
    )

    bess_string_total_energy_discharged_kwh_d = _agg_first(
        var=Download.time_series.bess_string_total_energy_discharged_kwh_5m.var,
    )

    ##########################
    # take diff on daily level
    ##########################

    # meter

    meter_delivered_energy_kwh_d = Field(
        calc.DiffAndFilterCalc(
            energy_total_var=meter_total_delivered_energy_kwh_d.var,
            power_capacity_var=Validate.project_power_capacity_kw.var,
            max_capacity_factor=12,  # if discharging at full power
            # for half the day (12 hours)
            time_dim=Time.DATE_LOCAL,
        )
    )

    meter_consumed_energy_kwh_d = Field(
        calc.DiffAndFilterCalc(
            energy_total_var=meter_total_consumed_energy_kwh_d.var,
            power_capacity_var=Validate.project_power_capacity_kw.var,
            max_capacity_factor=12,  # if charging at full power
            # for half the day (12 hours)
            time_dim=Time.DATE_LOCAL,
        )
    )

    # aux

    project_energy_aux_meter_kwh_d = Field(
        calc.DiffAndFilterCalc(
            energy_total_var=project_total_aux_energy_kwh_d.var,
            power_capacity_var=Validate.project_power_capacity_kw.var,
            max_capacity_factor=24 * 0.1,  # if 10% aux power all day
            time_dim=Time.DATE_LOCAL,
        )
    )

    # circuit

    bess_circuit_energy_charged_kwh_d = Field(
        calc.DiffAndFilterCalc(
            energy_total_var=bess_circuit_total_energy_charged_kwh_d.var,
            power_capacity_var=Validate.bess_mv_circuit_meter_power_capacity_kw.var,
            max_capacity_factor=12,  # if charging at full power
            time_dim=Time.DATE_LOCAL,
        )
    )
    bess_circuit_energy_discharged_kwh_d = Field(
        calc.DiffAndFilterCalc(
            energy_total_var=bess_circuit_total_energy_discharged_kwh_d.var,
            power_capacity_var=Validate.bess_mv_circuit_meter_power_capacity_kw.var,
            max_capacity_factor=12,  # if discharging at full power
            time_dim=Time.DATE_LOCAL,
        )
    )

    # pcs

    bess_pcs_energy_charged_kwh_d = Field(
        calc.DiffAndFilterCalc(
            energy_total_var=bess_pcs_total_energy_charged_kwh_d.var,
            power_capacity_var=Validate.bess_pcs_power_capacity_kw.var,
            max_capacity_factor=12,  # if charging at full power
            time_dim=Time.DATE_LOCAL,
        )
    )

    bess_pcs_energy_discharged_kwh_d = Field(
        calc.DiffAndFilterCalc(
            energy_total_var=bess_pcs_total_energy_discharged_kwh_d.var,
            power_capacity_var=Validate.bess_pcs_power_capacity_kw.var,
            max_capacity_factor=12,  # if discharging at full power
            time_dim=Time.DATE_LOCAL,
        )
    )
    # pcs module

    bess_pcs_module_energy_charged_kwh_d = Field(
        calc.DiffAndFilterCalc(
            energy_total_var=bess_pcs_module_total_energy_charged_kwh_d.var,
            power_capacity_var=Validate.bess_pcs_module_power_capacity_kw.var,
            max_capacity_factor=12,  # if charging at full power
            time_dim=Time.DATE_LOCAL,
        )
    )
    bess_pcs_module_energy_discharged_kwh_d = Field(
        calc.DiffAndFilterCalc(
            energy_total_var=bess_pcs_module_total_energy_discharged_kwh_d.var,
            power_capacity_var=Validate.bess_pcs_module_power_capacity_kw.var,
            max_capacity_factor=12,  # if discharging at full power
            time_dim=Time.DATE_LOCAL,
        )
    )

    # string

    bess_string_energy_charged_kwh_d = Field(
        calc.DiffAndFilterCalc(
            energy_total_var=bess_string_total_energy_charged_kwh_d.var,
            power_capacity_var=Validate.bess_string_power_capacity_kw.var,
            max_capacity_factor=12,  # if charging at full power
            time_dim=Time.DATE_LOCAL,
        )
    )

    bess_string_energy_discharged_kwh_d = Field(
        calc.DiffAndFilterCalc(
            energy_total_var=bess_string_total_energy_discharged_kwh_d.var,
            power_capacity_var=Validate.bess_string_power_capacity_kw.var,
            max_capacity_factor=12,  # if discharging at full power
            time_dim=Time.DATE_LOCAL,
        )
    )

    #########################################################
    # Aggregate across device to project level
    #########################################################

    # circuit

    project_energy_charged_circuit_kwh_d = _device_aggregate(
        var=bess_circuit_energy_charged_kwh_d.var,
        agg=Aggregation.SUM,
        child_device_axis=DeviceType.BESS_MV_CIRCUIT_METER,
    )
    project_energy_discharged_circuit_kwh_d = _device_aggregate(
        var=bess_circuit_energy_discharged_kwh_d.var,
        agg=Aggregation.SUM,
        child_device_axis=DeviceType.BESS_MV_CIRCUIT_METER,
    )

    # pcs

    project_energy_charged_pcs_kwh_d = _device_aggregate(
        var=bess_pcs_energy_charged_kwh_d.var,
        agg=Aggregation.SUM,
        child_device_axis=DeviceType.BESS_PCS,
    )
    project_energy_discharged_pcs_kwh_d = _device_aggregate(
        var=bess_pcs_energy_discharged_kwh_d.var,
        agg=Aggregation.SUM,
        child_device_axis=DeviceType.BESS_PCS,
    )

    # pcs module

    project_energy_charged_pcs_module_kwh_d = _device_aggregate(
        var=bess_pcs_module_energy_charged_kwh_d.var,
        agg=Aggregation.SUM,
        child_device_axis=DeviceType.BESS_PCS_MODULE,
    )
    project_energy_discharged_pcs_module_kwh_d = _device_aggregate(
        var=bess_pcs_module_energy_discharged_kwh_d.var,
        agg=Aggregation.SUM,
        child_device_axis=DeviceType.BESS_PCS_MODULE,
    )

    # string

    project_energy_charged_string_kwh_d = _device_aggregate(
        var=bess_string_energy_charged_kwh_d.var,
        agg=Aggregation.SUM,
        child_device_axis=DeviceType.BESS_STRING,
    )

    project_energy_discharged_string_kwh_d = _device_aggregate(
        var=bess_string_energy_discharged_kwh_d.var,
        agg=Aggregation.SUM,
        child_device_axis=DeviceType.BESS_STRING,
    )

    #########################################################
    # other energy calculations
    #########################################################

    meter_consumed_energy_no_aux_kwh_d = Field(
        calc.LinearCombinationCalc(
            vars=[
                meter_consumed_energy_kwh_d.var,
                project_energy_aux_meter_kwh_d.var,
            ],
            coefficients=[1, -1],
        )
    )

    project_meter_to_pcs_module_charge_efficiency_d = Field(
        calc.EnergyEfficiencyCalc(
            energy_source_kwh_var=meter_consumed_energy_kwh_d.var,
            energy_sink_kwh_var=project_energy_charged_pcs_module_kwh_d.var,
            energy_capacity_kwh_var=Validate.project_energy_capacity_kwh.var,
            min_source_energy_capacity_factor=0.2,
            max_efficiency=1.0,
        )
    )

    project_pcs_module_to_meter_discharge_efficiency_d = Field(
        calc.EnergyEfficiencyCalc(
            energy_source_kwh_var=project_energy_discharged_pcs_module_kwh_d.var,
            energy_sink_kwh_var=meter_delivered_energy_kwh_d.var,
            energy_capacity_kwh_var=Validate.project_energy_capacity_kwh.var,
            min_source_energy_capacity_factor=0.2,
            max_efficiency=1.0,
        )
    )

    bess_string_avg_c_rate_d = Field(
        calc.DailyAverageCRateCalc(
            daily_energy_charged_var=bess_string_energy_charged_kwh_d.var,
            daily_energy_discharged_var=bess_string_energy_discharged_kwh_d.var,
            energy_capacity_var=Validate.project_energy_capacity_kwh.var,
        )
    )

    project_avg_string_c_rate_d = Field(
        calc.DailyAverageCRateCalc(
            daily_energy_charged_var=project_energy_charged_string_kwh_d.var,
            daily_energy_discharged_var=project_energy_discharged_string_kwh_d.var,
            energy_capacity_var=Validate.project_energy_capacity_kwh.var,
        )
    )

    bess_string_avg_c_rate_while_charging_d = Field(
        calc.DailyAverageCRateChargingCalc(
            daily_energy_charged_var=bess_string_energy_charged_kwh_d.var,
            energy_capacity_var=Validate.project_energy_capacity_kwh.var,
        )
    )

    project_avg_string_c_rate_while_charging_d = Field(
        calc.DailyAverageCRateChargingCalc(
            daily_energy_charged_var=project_energy_charged_string_kwh_d.var,
            energy_capacity_var=Validate.project_energy_capacity_kwh.var,
        )
    )

    bess_string_avg_c_rate_while_discharging_d = Field(
        calc.DailyAverageCRateChargingCalc(
            daily_energy_charged_var=bess_string_energy_discharged_kwh_d.var,
            energy_capacity_var=Validate.project_energy_capacity_kwh.var,
        )
    )

    project_avg_string_c_rate_while_discharging_d = Field(
        calc.DailyAverageCRateChargingCalc(
            daily_energy_charged_var=project_energy_discharged_string_kwh_d.var,
            energy_capacity_var=Validate.project_energy_capacity_kwh.var,
        )
    )

    # ============================================================================
    # Continuous Discharge Calculations
    # ============================================================================

    # bess_string_maximum_continuous_discharge_kwh_d = Field(
    #     calc.MaximumContinuousDischargeCalc(
    #         energy_discharged_kwh_var=Calculate.bess_string_energy_discharged_kwh_5m.var,
    #         energy_charged_kwh_var=Calculate.bess_string_energy_charged_kwh_5m.var,
    #         energy_capacity_kwh_var=Validate.bess_string_energy_capacity_kwh.var,
    #         time_combiner_model=_5min_to_daily(),
    #     )
    # )

    # project_maximum_continuous_discharge_across_strings_kwh_d = Field(
    #     calc.MaximumContinuousDischargeCalc(
    #         energy_discharged_kwh_var=Calculate.bess_string_energy_discharged_kwh_5m.var,
    #         energy_charged_kwh_var=Calculate.bess_string_energy_charged_kwh_5m.var,
    #         energy_capacity_kwh_var=Validate.bess_string_energy_capacity_kwh.var,
    #         device_combiner_model=CoordCombinerModel(
    #             child_device_axis=DeviceType.BESS_STRING,
    #         ),
    #         time_combiner_model=_5min_to_daily(),
    #     )
    # )

    project_maximum_continuous_discharge_kwh_d = Field(
        calc.MaximumContinuousDischargeCalc(
            energy_discharged_kwh_5m_var=Calculate.meter_delivered_energy_kwh_5m.var,
            energy_charged_kwh_5m_var=Calculate.meter_consumed_energy_kwh_5m.var,
            energy_capacity_kwh_var=Validate.project_energy_capacity_kwh.var,
            time_combiner_model=_5min_to_daily(),
        )
    )

    # bess_pcs_module_maximum_continuous_discharge_kwh_d = Field(
    #     calc.MaximumContinuousDischargeCalc(
    #         energy_discharged_kwh_var=Calculate.bess_pcs_module_energy_discharged_kwh_5m.var,
    #         energy_charged_kwh_var=Calculate.bess_pcs_module_energy_charged_kwh_5m.var,
    #         energy_capacity_kwh_var=Validate.bess_pcs_module_energy_capacity_kwh.var,
    #         time_combiner_model=_5min_to_daily(),
    #     )
    # )

    # project_maximum_continuous_discharge_across_pcs_modules_kwh_d = Field(
    #     calc.MaximumContinuousDischargeCalc(
    #         energy_discharged_kwh_var=Calculate.bess_pcs_module_energy_discharged_kwh_5m.var,
    #         energy_charged_kwh_var=Calculate.bess_pcs_module_energy_charged_kwh_5m.var,
    #         energy_capacity_kwh_var=Validate.bess_pcs_module_energy_capacity_kwh.var,
    #         device_combiner_model=CoordCombinerModel(
    #             child_device_axis=DeviceType.BESS_PCS_MODULE,
    #         ),
    #         time_combiner_model=_5min_to_daily(),
    #     )
    # )

    # bess_pcs_maximum_continuous_discharge_kwh_d = Field(
    #     calc.MaximumContinuousDischargeCalc(
    #         energy_discharged_kwh_var=Calculate.bess_pcs_energy_discharged_kwh_5m.var,
    #         energy_charged_kwh_var=Calculate.bess_pcs_energy_charged_kwh_5m.var,
    #         energy_capacity_kwh_var=Validate.bess_pcs_energy_capacity_kwh.var,
    #         time_combiner_model=_5min_to_daily(),
    #     )
    # )

    # project_maximum_continuous_discharge_across_pcs_kwh_d = Field(
    #     calc.MaximumContinuousDischargeCalc(
    #         energy_discharged_kwh_var=Calculate.bess_pcs_energy_discharged_kwh_5m.var,
    #         energy_charged_kwh_var=Calculate.bess_pcs_energy_charged_kwh_5m.var,
    #         energy_capacity_kwh_var=Validate.bess_pcs_energy_capacity_kwh.var,
    #         device_combiner_model=CoordCombinerModel(
    #             child_device_axis=DeviceType.BESS_PCS,
    #         ),
    #         time_combiner_model=_5min_to_daily(),
    #     )
    # )
