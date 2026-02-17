from kpi_pipeline.base.field import Field
from kpi_pipeline.config.step_01_download import Download
from kpi_pipeline.config.step_02_validate.utils import _capacity
from kpi_pipeline.services.calc import FilterByCapacityCalc
from kpi_pipeline.services.schema import AddCalculationsSchema


class ValidateGeneral(AddCalculationsSchema):
    _update = True

    project_power_capacity_kw = _capacity(
        Download.project_attributes.project_power_capacity_kw.var
    )

    project_power_kw_5m = Field(
        FilterByCapacityCalc(
            data_var=Download.time_series.project_power_kw_5m.var,
            capacity_var=Download.project_attributes.project_power_capacity_kw.var,
            min_capacity_factor=-1.0,
            max_capacity_factor=1.0,
        )
    )
