from kpi.domain.agg.resample import resample_diff_mod
from kpi.domain.util import diff_mod
from kpi.op.transform.arg import Constant, Grouper, Required
from kpi.op.transform.method import calc_field
from kpi.registry.transform.pv.api import Transform


class DoubleBlackDiamondTransform(Transform):
    allow_override = True

    project_energy_exported_to_grid_unfiltered_kwh_5m = calc_field(diff_mod)(
        Required(Transform.project_total_energy_exported_to_grid_filled_kwh_5m),
        modulus=Constant(1_000_000_000),
    )

    project_energy_production_unfiltered_kwh_d = calc_field(resample_diff_mod)(
        Required(Transform.project_total_energy_exported_to_grid_filled_kwh_5m),
        grouper=Grouper(Transform.date_local_5m),
        modulus=Constant(1_000_000_000),
    )
