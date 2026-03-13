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
            modulus=65_536,  # 16-bit unsigned integer
            max_positive_step=150_000,
        )
    )
    meter_total_delivered_energy_kwh_5m = Field(
        calc.ReconstructAccumulatorCalc(
            total_energy_kw_5m_var=Download.time_series.meter_total_delivered_energy_kwh_5m.var,
            modulus=65_536,  # 16-bit unsigned integer
            max_positive_step=150_000,
        )
    )
    bess_circuit_total_energy_charged_kwh_5m = Field(
        calc.ReconstructAccumulatorCalc(
            total_energy_kw_5m_var=Download.time_series.bess_circuit_total_energy_charged_kwh_5m.var,
            modulus=65_536,  # 16-bit unsigned integer
            max_positive_step=40_000,
        )
    )
    bess_circuit_total_energy_discharged_kwh_5m = Field(
        calc.ReconstructAccumulatorCalc(
            total_energy_kw_5m_var=Download.time_series.bess_circuit_total_energy_discharged_kwh_5m.var,
            modulus=65_536,  # 16-bit unsigned integer
            max_positive_step=40_000,
        )
    )

    bess_string_total_energy_charged_kwh_5m = Field(
        calc.ReconstructAccumulatorCalc(
            total_energy_kw_5m_var=Download.time_series.bess_string_total_energy_charged_kwh_5m.var,
            modulus=6_553.6,  # 16-bit signed integer
            max_positive_step=500,
        )
    )
    bess_string_total_energy_discharged_kwh_5m = Field(
        calc.ReconstructAccumulatorCalc(
            total_energy_kw_5m_var=Download.time_series.bess_string_total_energy_discharged_kwh_5m.var,
            modulus=6_553.6,  # 16-bit signed integer
            max_positive_step=500,
        )
    )
