import kpi_pipeline.services.calc as calc
from kpi_pipeline.base.enums import Aggregation, Time
from kpi_pipeline.base.field import Field
from kpi_pipeline.config.helper_fields import _aggregate
from kpi_pipeline.config.step_02_validate import Validate
from kpi_pipeline.config.step_03_calculate import Calculate
from kpi_pipeline.config.step_04_aggregate import Aggregate


class AggregateBexar(Aggregate):
    ##########################
    # Sum from 5-minute level
    ##########################

    # the meter energy accumulators loop several times in a single day
    # so we need to sum the 5-minute values to get the daily total

    meter_delivered_energy_kwh_d = _aggregate(
        var=Calculate.meter_delivered_energy_kwh_5m.var,
        agg=Aggregation.SUM,
    )

    meter_consumed_energy_kwh_d = _aggregate(
        var=Calculate.meter_consumed_energy_kwh_5m.var,
        agg=Aggregation.SUM,
    )

    ##########################
    # Add specific modulus
    ##########################

    # aux

    project_energy_aux_meter_kwh_d = Field(
        calc.DiffAndFilterCalc(
            energy_total_var=Aggregate.project_total_aux_energy_kwh_d.var,
            modulus=65_536,  # 16-bit integer
            power_capacity_var=Validate.project_power_capacity_kw.var,
            max_capacity_factor=24 * 0.1,  # if 10% aux power all day
            time_dim=Time.DATE_LOCAL,
        )
    )

    # circuit

    bess_circuit_energy_charged_kwh_d = Field(
        calc.DiffAndFilterCalc(
            energy_total_var=Aggregate.bess_circuit_total_energy_charged_kwh_d.var,
            modulus=65_536,  # 16-bit integer
            power_capacity_var=Validate.bess_mv_circuit_meter_power_capacity_kw.var,
            max_capacity_factor=12,  # if string is charging at full power for 12 hours
            time_dim=Time.DATE_LOCAL,
        )
    )

    bess_circuit_energy_discharged_kwh_d = Field(
        calc.DiffAndFilterCalc(
            energy_total_var=Aggregate.bess_circuit_total_energy_discharged_kwh_d.var,
            modulus=65_536,  # 16-bit integer
            power_capacity_var=Validate.bess_mv_circuit_meter_power_capacity_kw.var,
            max_capacity_factor=12,  # if string is discharging at full power for 12 hours
            time_dim=Time.DATE_LOCAL,
        )
    )

    # string

    bess_string_energy_charged_kwh_d = Field(
        calc.DiffAndFilterCalc(
            energy_total_var=Aggregate.bess_string_total_energy_charged_kwh_d.var,
            modulus=6_553.6,  # 16-bit integer
            power_capacity_var=Validate.bess_string_power_capacity_kw.var,
            max_capacity_factor=12,  # if string is charging at full power for 12 hours
            time_dim=Time.DATE_LOCAL,
        )
    )

    bess_string_energy_discharged_kwh_d = Field(
        calc.DiffAndFilterCalc(
            energy_total_var=Aggregate.bess_string_total_energy_discharged_kwh_d.var,
            modulus=6_553.6,  # 16-bit integer
            power_capacity_var=Validate.bess_string_power_capacity_kw.var,
            max_capacity_factor=12,  # if string is discharging at full power for 12 hours
            time_dim=Time.DATE_LOCAL,
        )
    )
