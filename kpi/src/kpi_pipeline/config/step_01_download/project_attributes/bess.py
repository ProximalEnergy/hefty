from core.models import Project

from kpi_pipeline.base.field import Field
from kpi_pipeline.base.models import ProjectAttributeModel
from kpi_pipeline.services.schema import DownloadProjectAttributesSchema


class DownloadProjAttrsBESS(DownloadProjectAttributesSchema):
    project_energy_capacity_kwh = Field(
        ProjectAttributeModel(
            source_field_name=Project.capacity_bess_energy_bol_dc.name, scale=1000
        ),
    )

    project_power_capacity_kw = Field(
        ProjectAttributeModel(
            source_field_name=Project.capacity_bess_power_ac.name, scale=1000
        ),
    )
