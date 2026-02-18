from kpi_pipeline.base.field import Field
from kpi_pipeline.services.calc import CalcProcess, SelectCalc
from kpi_pipeline.services.process import VerifyWithinRangeProcess


def _capacity(field: str) -> Field:
    return Field(
        CalcProcess(
            calc=SelectCalc(var=field),
            process=VerifyWithinRangeProcess(min_value=0, left_inclusive=False),
        ),
    )
