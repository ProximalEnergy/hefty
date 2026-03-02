import kpi_pipeline.services.calc as calc
from kpi_pipeline.base.field import Field
from kpi_pipeline.config.step_01_download import Download
from kpi_pipeline.config.step_02_validate import Validate


class ValidateBexar(Validate):
    """
    This inherits from the base validation and only overwrites
    the fields defined below.
    """

    # Bexar uses a cycling integer value for it's accumulated energy
    # This validation transforms the modular increments into
    # an increasing monotonic function.
    meter_total_consumed_energy_kwh_5m = Field(
        calc.ReconstructAccumulatorCalc(
            total_energy_kw_5m_var=Download.time_series.meter_total_consumed_energy_kwh_5m.var,
            power_capacity_kw_var=Download.project_attributes.project_power_capacity_kw.var,
            modulo=65_536,  # 16-bit unsigned integer
        )
    )
    meter_total_delivered_energy_kwh_5m = Field(
        calc.ReconstructAccumulatorCalc(
            total_energy_kw_5m_var=Download.time_series.meter_total_delivered_energy_kwh_5m.var,
            power_capacity_kw_var=Download.project_attributes.project_power_capacity_kw.var,
            modulo=65_536,  # 16-bit unsigned integer
        )
    )
