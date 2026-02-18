from core import models

from kpi_pipeline.base.field import Field
from kpi_pipeline.base.models import ProjectAttributeModel
from kpi_pipeline.services.schema import DownloadProjectAttributesSchema


class DownloadProjAttrsGeneral(DownloadProjectAttributesSchema):
    project_poi_limit_kw = Field(
        ProjectAttributeModel(
            source_field_name=models.Project.poi.name,
            scale=1000,
        )
    )
