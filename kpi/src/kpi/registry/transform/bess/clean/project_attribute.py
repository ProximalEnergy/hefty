from kpi.domain.util import verify_positive
from kpi.op.transform.schema import CalcSchema
from kpi.op.transform.unary import unary_field
from kpi.registry.download.project_attribute.bess import DownloadProjectAttributeBess

T = DownloadProjectAttributeBess


class TransformBessCleanProjectAttribute(CalcSchema):
    project_energy_capacity_kwh = unary_field(
        verify_positive,
        field=T.project_energy_capacity_raw_kwh,
    )

    project_power_capacity_kw = unary_field(
        verify_positive,
        field=T.project_power_capacity_raw_kw,
    )

    project_poi_limit_kw = unary_field(
        verify_positive,
        field=T.project_poi_limit_raw_kw,
    )
