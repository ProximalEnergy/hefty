from core import models

from kpi_pipeline.base.field import Field
from kpi_pipeline.base.models import ProjectAttributeModel
from kpi_pipeline.services.schema import DownloadProjectAttributesSchema


class DownloadProjAttrsPV(DownloadProjectAttributesSchema):
    project_power_capacity_dc_kw = Field(
        ProjectAttributeModel(
            source_field_name=models.Project.capacity_dc.name,
            scale=1000,
        )
    )
