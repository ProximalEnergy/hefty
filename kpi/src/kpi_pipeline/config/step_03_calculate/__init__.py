from kpi_pipeline.config.step_03_calculate.bess import CalculateBESS
from kpi_pipeline.config.step_03_calculate.pv import CalculatePV


class Calculate(CalculateBESS, CalculatePV):
    pass
