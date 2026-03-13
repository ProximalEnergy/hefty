from core.enumerations import DeviceType

import kpi_pipeline.services.calc as calc
import kpi_pipeline.services.process as process
from kpi_pipeline.base.enums import Aggregation, Time
from kpi_pipeline.base.field import Field
from kpi_pipeline.config.helper_fields import (
    _5min_to_daily,
    _agg_first,
    _aggregate,
    _device_aggregate,
)
from kpi_pipeline.config.step_02_validate import Validate
from kpi_pipeline.config.step_03_calculate import Calculate
from kpi_pipeline.services.schema import AddCalculationsSchema


class AggregateBESSEnergy(AddCalculationsSchema):
    # ============================================================================
    # Energy Aggregations
    # ============================================================================
    # Aggregates energy metrics from 5-minute to daily by summing or accumulating
    # energy charged, discharged, and auxiliary energy consumption

    project_total_aux_energy_kwh_d = _agg_first(
        var=Validate.project_total_aux_energy_kwh_5m.var,
    )

    project_energy_aux_meter_kwh_d = Field(
        calc.ProcessCalc(
            var=project_total_aux_energy_kwh_d.var,
            process=process.DiffProcess(time_dim=Time.DATE_LOCAL),
        )
    )

    bess_string_total_energy_charged_kwh_d = _agg_first(
        var=Validate.bess_string_total_energy_charged_kwh_5m.var,
    )

    bess_string_total_energy_discharged_kwh_d = _agg_first(
        var=Validate.bess_string_total_energy_discharged_kwh_5m.var,
    )

    bess_string_energy_charged_kwh_d = Field(
        calc.ProcessCalc(
            var=bess_string_total_energy_charged_kwh_d.var,
            process=process.DiffProcess(time_dim=Time.DATE_LOCAL),
        )
    )

    bess_string_energy_discharged_kwh_d = Field(
        calc.ProcessCalc(
            var=bess_string_total_energy_discharged_kwh_d.var,
            process=process.DiffProcess(time_dim=Time.DATE_LOCAL),
        )
    )

    meter_total_delivered_energy_kwh_d = _agg_first(
        var=Validate.meter_total_delivered_energy_kwh_5m.var,
    )

    meter_total_consumed_energy_kwh_d = _agg_first(
        var=Validate.meter_total_consumed_energy_kwh_5m.var,
    )

    meter_delivered_energy_kwh_d = Field(
        calc.ProcessCalc(
            var=meter_total_delivered_energy_kwh_d.var,
            process=process.DiffProcess(time_dim=Time.DATE_LOCAL),
        )
    )

    meter_consumed_energy_kwh_d = Field(
        calc.ProcessCalc(
            var=meter_total_consumed_energy_kwh_d.var,
            process=process.DiffProcess(time_dim=Time.DATE_LOCAL),
        )
    )

    meter_consumed_energy_no_aux_kwh_d = Field(
        calc.LinearCombinationCalc(
            vars=[
                meter_consumed_energy_kwh_d.var,
                project_energy_aux_meter_kwh_d.var,
            ],
            coefficients=[1, -1],
        )
    )

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

    bess_pcs_energy_charged_kwh_d = _aggregate(
        var=Calculate.bess_pcs_energy_charged_kwh_5m.var,
        agg=Aggregation.SUM,
    )
    project_energy_charged_pcs_kwh_d = _aggregate(
        var=Calculate.bess_pcs_energy_charged_kwh_5m.var,
        agg=Aggregation.SUM,
        child_device_axis=DeviceType.BESS_PCS,
    )
    bess_pcs_energy_discharged_kwh_d = _aggregate(
        var=Calculate.bess_pcs_energy_discharged_kwh_5m.var,
        agg=Aggregation.SUM,
    )
    project_energy_discharged_pcs_kwh_d = _aggregate(
        var=Calculate.bess_pcs_energy_discharged_kwh_5m.var,
        agg=Aggregation.SUM,
        child_device_axis=DeviceType.BESS_PCS,
    )

    bess_pcs_module_energy_charged_kwh_d = _aggregate(
        var=Calculate.bess_pcs_module_energy_charged_kwh_5m.var,
        agg=Aggregation.SUM,
    )
    project_energy_charged_pcs_module_kwh_d = _aggregate(
        var=Calculate.bess_pcs_module_energy_charged_kwh_5m.var,
        agg=Aggregation.SUM,
        child_device_axis=DeviceType.BESS_PCS_MODULE,
    )
    bess_pcs_module_energy_discharged_kwh_d = _aggregate(
        var=Calculate.bess_pcs_module_energy_discharged_kwh_5m.var,
        agg=Aggregation.SUM,
    )
    project_energy_discharged_pcs_module_kwh_d = _aggregate(
        var=Calculate.bess_pcs_module_energy_discharged_kwh_5m.var,
        agg=Aggregation.SUM,
        child_device_axis=DeviceType.BESS_PCS_MODULE,
    )

    bess_circuit_total_energy_charged_kwh_d = _agg_first(
        var=Validate.bess_circuit_total_energy_charged_kwh_5m.var,
    )
    bess_circuit_total_energy_discharged_kwh_d = _agg_first(
        var=Validate.bess_circuit_total_energy_discharged_kwh_5m.var,
    )

    bess_circuit_energy_charged_kwh_d = Field(
        calc.ProcessCalc(
            var=bess_circuit_total_energy_charged_kwh_d.var,
            process=process.DiffProcess(time_dim=Time.DATE_LOCAL),
        )
    )
    bess_circuit_energy_discharged_kwh_d = Field(
        calc.ProcessCalc(
            var=bess_circuit_total_energy_discharged_kwh_d.var,
            process=process.DiffProcess(time_dim=Time.DATE_LOCAL),
        )
    )
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
            total_energy_discharged_kwh_5m_var=Validate.meter_total_delivered_energy_kwh_5m.var,
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
