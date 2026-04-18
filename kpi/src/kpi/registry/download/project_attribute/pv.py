from kpi.base.protocol import ProjectAttributeProtocol
from kpi.op.download.project_attribute import (
    Latitude,
    Longitude,
    project_attribute_field,
)
from kpi.op.field import MakeField
from kpi.op.field_registry import FieldRegistry

from core import models

field = MakeField[ProjectAttributeProtocol].infer_doc


class DownloadProjectAttributePv(FieldRegistry[ProjectAttributeProtocol]):
    project_dc_capacity_raw_kw = project_attribute_field(
        source_field_name=models.Project.capacity_dc.name,
        scale=1000,
    )

    project_latitude_raw_deg = field(Latitude())

    project_longitude_raw_deg = field(Longitude())

    project_elevation_raw_m = project_attribute_field(
        source_field_name=models.Project.elevation.name,
    )
