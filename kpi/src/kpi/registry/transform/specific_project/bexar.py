from typing import override

import xarray as xr
from kpi.base.enumeration import TimeCoord
from kpi.domain.agg.resample import resample_sum
from kpi.domain.bess import daily_energy
from kpi.domain.util import diff, filter_mask, rename
from kpi.op.transform.arg import Constant, Required
from kpi.op.transform.method import calc_field, method_calc
from kpi.registry.transform.bess.api import TransformBess
from kpi.registry.transform.pv.api import Transform


class BexarTransform(Transform):
    allow_override = True

    @method_calc(
        energy_total=Required(TransformBess.project_total_energy_charged_filled_kwh_5m),
        power_capacity=Required(Transform.project_power_capacity_kw),
    )
    @override
    def project_energy_charged_kwh_5m(
        energy_total: xr.DataArray,
        power_capacity: xr.DataArray,
    ) -> xr.DataArray:
        """
        Include a rollover value to handle the 16-bit integer overflow.
        """
        difference = diff(energy_total)
        epsilon = 1e-6
        mod_diff = ((difference + epsilon) % 65_536) - epsilon

        clean_diff = mod_diff.where(
            filter_mask(
                filter_by=mod_diff / power_capacity,
                max_value=1 / 12 + epsilon,
            )
        )
        return clean_diff

    @method_calc(
        energy_total=Required(
            TransformBess.project_total_energy_discharged_filled_kwh_5m
        ),
        power_capacity=Required(TransformBess.project_power_capacity_kw),
    )
    @override
    def project_energy_discharged_kwh_5m(
        energy_total: xr.DataArray,
        power_capacity: xr.DataArray,
    ) -> xr.DataArray:
        """
        Include a rollover value to handle the 16-bit integer overflow.
        """
        difference = diff(energy_total)
        epsilon = 1e-6
        mod_diff = ((difference + epsilon) % 65_536) - epsilon

        clean_diff = mod_diff.where(
            filter_mask(
                filter_by=mod_diff / power_capacity,
                max_value=1 / 12 + epsilon,
            )
        )
        return clean_diff

    project_energy_discharged_kwh_d = calc_field(resample_sum)(
        Required(project_energy_discharged_kwh_5m),
        grouper=Required(TransformBess.date_local_5m),
    )

    project_energy_charged_kwh_d = calc_field(resample_sum)(
        Required(project_energy_charged_kwh_5m),
        grouper=Required(TransformBess.date_local_5m),
    )

    @method_calc(
        total_energy_5m=Required(TransformBess.project_total_aux_energy_filled_kwh_5m),
        power_capacity=Required(TransformBess.project_power_capacity_kw),
        date_local_5m=Required(TransformBess.date_local_5m),
    )
    @override
    def project_aux_energy_kwh_d(
        total_energy_5m: xr.DataArray,
        power_capacity: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        """
        Project Auxiliary Energy Per Day
        Takes the accumulator differences between midnight and midnight the next day
        and filters out any negatives values or days where the aux energy is greater
        than the equivalent of 24 hours of 10% of the project's power capacity.
        Include 16-bit integer overflow handling.
        """
        total_energy_d = total_energy_5m.groupby(rename(date_local_5m)).first()
        difference = diff(total_energy_d, time_dim=TimeCoord.DATE_LOCAL)
        epsilon = 1e-6
        difference = ((difference + epsilon) % 65_536) - epsilon
        difference = difference.where(
            filter_mask(
                filter_by=difference / power_capacity,
                min_value=-epsilon,
                max_value=24 * 0.1,
            )
        )
        return difference

    circuit_energy_charged_kwh_d = calc_field(daily_energy)(
        total_energy_5m=Required(
            TransformBess.circuit_total_energy_charged_filled_kwh_5m
        ),
        energy_capacity=Required(TransformBess.circuit_energy_capacity_kwh),
        date_local_5m=Required(TransformBess.date_local_5m),
        modulus=Constant(65_536),
    )

    circuit_energy_discharged_kwh_d = calc_field(daily_energy)(
        total_energy_5m=Required(
            TransformBess.circuit_total_energy_discharged_filled_kwh_5m
        ),
        energy_capacity=Required(TransformBess.circuit_energy_capacity_kwh),
        date_local_5m=Required(TransformBess.date_local_5m),
        modulus=Constant(65_536),
    )

    string_energy_charged_kwh_d = calc_field(daily_energy)(
        total_energy_5m=Required(
            TransformBess.string_total_energy_charged_filled_kwh_5m
        ),
        energy_capacity=Required(TransformBess.string_energy_capacity_kwh),
        date_local_5m=Required(TransformBess.date_local_5m),
        modulus=Constant(6_553.6),
    )

    string_energy_discharged_kwh_d = calc_field(daily_energy)(
        total_energy_5m=Required(
            TransformBess.string_total_energy_discharged_filled_kwh_5m
        ),
        energy_capacity=Required(TransformBess.string_energy_capacity_kwh),
        date_local_5m=Required(TransformBess.date_local_5m),
        modulus=Constant(6_553.6),
    )
