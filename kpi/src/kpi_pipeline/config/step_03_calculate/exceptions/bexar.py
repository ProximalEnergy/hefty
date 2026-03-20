import kpi_pipeline.services.calc as calc
from kpi_pipeline.base.field import Field
from kpi_pipeline.config.step_02_validate import Validate
from kpi_pipeline.config.step_03_calculate import Calculate


class CalculateBexar(Calculate):
    meter_consumed_energy_kwh_5m = Field(
        calc.DiffAndFilterCalc(
            energy_total_var=Calculate.meter_total_consumed_energy_filled_5m.var,
            power_capacity_var=Validate.project_power_capacity_kw.var,
            modulus=65_536,  # 16-bit integer
            max_capacity_factor=1 / 12,  # 12 steps per hour
        )
    )

    meter_delivered_energy_kwh_5m = Field(
        calc.DiffAndFilterCalc(
            energy_total_var=Calculate.meter_total_delivered_energy_filled_5m.var,
            power_capacity_var=Validate.project_power_capacity_kw.var,
            modulus=65_536,  # 16-bit integer
            max_capacity_factor=1 / 12,  # 12 steps per hour
        )
    )
