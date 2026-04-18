from kpi.base.protocol import ProjectAttributeProtocol
from kpi.op.download.project_attribute import (
    project_attribute_field,
)
from kpi.op.field_registry import FieldRegistry

from core import models


class DownloadProjectAttributeBess(FieldRegistry[ProjectAttributeProtocol]):
    project_energy_capacity_raw_kwh = project_attribute_field(
        source_field_name=models.Project.capacity_bess_energy_bol_dc.name,
        scale=1000,
    )

    project_power_capacity_raw_kw = project_attribute_field(
        source_field_name=models.Project.capacity_bess_power_ac.name,
        scale=1000,
    )

    project_poi_limit_raw_kw = project_attribute_field(
        source_field_name=models.Project.poi.name,
        scale=1000,
    )
