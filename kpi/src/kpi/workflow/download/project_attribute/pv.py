from kpi.service.download.project_attribute import (
    Latitude,
    Longitude,
    ProjectAttributeSchema,
    project_attribute_field,
)
from kpi.service.field import Field

from core import models

field = project_attribute_field


class DownloadProjectAttributePv(ProjectAttributeSchema):
    project_dc_capacity_raw_kw = field(
        source_field_name=models.Project.capacity_dc.name,
        scale=1000,
    )

    project_latitude_raw_deg = Field(Latitude())

    project_longitude_raw_deg = Field(Longitude())

    project_elevation_raw_m = field(
        source_field_name=models.Project.elevation.name,
    )
