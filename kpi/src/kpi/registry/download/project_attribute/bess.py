from kpi.op.download.project_attribute import (
    ProjectAttributeSchema,
    project_attribute_field,
)

from core import models

field = project_attribute_field


class DownloadProjectAttributeBess(ProjectAttributeSchema):
    project_energy_capacity_raw_kwh = field(
        source_field_name=models.Project.capacity_bess_energy_bol_dc.name,
        scale=1000,
    )

    project_power_capacity_raw_kw = field(
        source_field_name=models.Project.capacity_bess_power_ac.name,
        scale=1000,
    )

    project_poi_limit_raw_kw = field(
        source_field_name=models.Project.poi.name,
        scale=1000,
    )
