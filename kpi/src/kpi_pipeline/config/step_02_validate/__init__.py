from kpi_pipeline.config.step_02_validate.bess import ValidateBESS
from kpi_pipeline.config.step_02_validate.general import ValidateGeneral
from kpi_pipeline.config.step_02_validate.pv import ValidatePV


class Validate(ValidateGeneral, ValidateBESS, ValidatePV):
    pass
