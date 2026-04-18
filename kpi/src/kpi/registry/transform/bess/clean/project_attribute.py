from kpi.base.protocol import CalcProtocol
from kpi.domain.util import verify_positive
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.unary import unary_field
from kpi.registry.download.project_attribute.bess import (
    DownloadProjectAttributeBess as Download,
)


class TransformBessCleanProjectAttribute(FieldRegistry[CalcProtocol]):
    project_energy_capacity_kwh = unary_field(
        verify_positive,
        field=Download.project_energy_capacity_raw_kwh,
    )

    project_power_capacity_kw = unary_field(
        verify_positive,
        field=Download.project_power_capacity_raw_kw,
    )

    project_poi_limit_kw = unary_field(
        verify_positive,
        field=Download.project_poi_limit_raw_kw,
    )
