from kpi.domain.agg.resample import resample_diff_mod, resample_sum
from kpi.domain.util import diff_mod
from kpi.op.transform.arg import Constant, grouper, required
from kpi.op.transform.method import calc_field
from kpi.registry.transform.bess.api import TransformBess
from kpi.registry.transform.pv.api import Transform


class BexarTransform(Transform):
    allow_override = True

    project_energy_charged_unfiltered_kwh_5m = calc_field(diff_mod)(
        required(TransformBess.project_total_energy_charged_filled_kwh_5m),
        modulus=Constant(value=65536),
    )

    project_energy_discharged_unfiltered_kwh_5m = calc_field(diff_mod)(
        required(TransformBess.project_total_energy_discharged_filled_kwh_5m),
        modulus=Constant(value=65536),
    )

    project_energy_discharged_kwh_d = calc_field(resample_sum)(
        required(TransformBess.project_energy_discharged_kwh_5m),
        grouper=grouper(TransformBess.date_local_5m),
    )

    project_energy_charged_kwh_d = calc_field(resample_sum)(
        required(TransformBess.project_energy_charged_kwh_5m),
        grouper=grouper(TransformBess.date_local_5m),
    )

    project_aux_energy_unfiltered_kwh_d = calc_field(resample_diff_mod)(
        required(TransformBess.project_total_aux_energy_filled_kwh_5m),
        grouper=grouper(TransformBess.date_local_5m),
        modulus=Constant(value=65536),
    )

    circuit_energy_charged_unfiltered_kwh_d = calc_field(resample_diff_mod)(
        required(TransformBess.circuit_total_energy_charged_filled_kwh_5m),
        grouper=grouper(TransformBess.date_local_5m),
        modulus=Constant(value=65536),
    )

    circuit_energy_discharged_unfiltered_kwh_d = calc_field(resample_diff_mod)(
        required(TransformBess.circuit_total_energy_discharged_filled_kwh_5m),
        grouper=grouper(TransformBess.date_local_5m),
        modulus=Constant(value=65536),
    )

    string_energy_charged_unfiltered_kwh_d = calc_field(resample_diff_mod)(
        required(TransformBess.string_total_energy_charged_filled_kwh_5m),
        grouper=grouper(TransformBess.date_local_5m),
        modulus=Constant(value=6553.6),
    )

    string_energy_discharged_unfiltered_kwh_d = calc_field(resample_diff_mod)(
        required(TransformBess.string_total_energy_discharged_filled_kwh_5m),
        grouper=grouper(TransformBess.date_local_5m),
        modulus=Constant(value=6553.6),
    )
