from kpi.base.protocol import ProjectAttributeProtocol
from kpi.service.download.project_attribute import (
    Latitude,
    Longitude,
    ProjectAttributeSchema,
    project_attribute_field,
)
from kpi.service.field import MakeField

from core import models

field = MakeField[ProjectAttributeProtocol].infer_doc


class DownloadProjectAttributePv(ProjectAttributeSchema):
    project_dc_capacity_raw_kw = project_attribute_field(
        source_field_name=models.Project.capacity_dc.name,
        scale=1000,
    )

    project_latitude_raw_deg = field(Latitude())

    project_longitude_raw_deg = field(Longitude())

    project_elevation_raw_m = project_attribute_field(
        source_field_name=models.Project.elevation.name,
    )
