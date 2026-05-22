from core import models
from kpi.base.protocol import ProjectAttributeProtocol
from kpi.op.download.project_attribute import (
    Latitude,
    Longitude,
    project_attribute_field,
)
from kpi.op.field import Field
from kpi.op.field_registry import FieldRegistry


class DownloadProjectAttributePv(FieldRegistry[ProjectAttributeProtocol]):
    project_dc_power_capacity_raw_kw = project_attribute_field(
        source_field_name=models.Project.capacity_dc.name,
        scale=1000,
    )

    project_ac_power_capacity_raw_kw = project_attribute_field(
        source_field_name=models.Project.capacity_ac.name,
        scale=1000,
    )

    project_latitude_raw_deg = Field[ProjectAttributeProtocol](Latitude())

    project_longitude_raw_deg = Field[ProjectAttributeProtocol](Longitude())

    project_elevation_raw_m = project_attribute_field(
        source_field_name=models.Project.elevation.name,
    )
