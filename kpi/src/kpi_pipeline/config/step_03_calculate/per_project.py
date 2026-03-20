from kpi_pipeline.config.step_03_calculate import Calculate
from kpi_pipeline.config.step_03_calculate.exceptions.bexar import CalculateBexar

calculate_per_project = {
    "base": Calculate,
    "bexar": CalculateBexar,
}
