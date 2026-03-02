from kpi_pipeline.config.step_02_validate import Validate
from kpi_pipeline.config.step_02_validate.exceptions.bexar import ValidateBexar

validate_per_project = {
    "base": Validate,
    "bexar": ValidateBexar,
}
