from kpi.domain.util import verify_positive
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.arg import required
from kpi.op.transform.method import MethodCalc, calc_field
from kpi.registry.download.project_attribute.bess import (
    DownloadProjectAttributeBess as Download,
)


class TransformBessCleanProjectAttribute(FieldRegistry[MethodCalc]):
    project_energy_capacity_kwh = calc_field(verify_positive)(
        required(Download.project_energy_capacity_raw_kwh)
    )

    project_power_capacity_kw = calc_field(verify_positive)(
        required(Download.project_power_capacity_raw_kw)
    )

    project_poi_limit_kw = calc_field(verify_positive)(
        required(Download.project_poi_limit_raw_kw)
    )
