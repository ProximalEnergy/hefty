from typing import override

import xarray as xr
from kpi.domain.bess import daily_energy
from kpi.domain.util import date_local, diff, filter_mask
from kpi.op.transform.method import Input, method_calc
from kpi.registry.transform.bess.api import TransformBess
from kpi.registry.transform.pv.api import Transform


class BexarTransform(Transform, allow_override=True):
    @method_calc
    @override
    def project_energy_charged_kwh_5m(
        energy_total: xr.DataArray = Input(
            TransformBess.project_total_energy_charged_filled_kwh_5m
        ),
        power_capacity: xr.DataArray = Input(Transform.project_power_capacity_kw),
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

    @method_calc
    @override
    def project_energy_discharged_kwh_5m(
        energy_total: xr.DataArray = Input(
            TransformBess.project_total_energy_discharged_filled_kwh_5m
        ),
        power_capacity: xr.DataArray = Input(
            TransformBess.project_power_capacity_kw
        ),
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

    @method_calc
    @override
    def project_energy_discharged_kwh_d(
        energy: xr.DataArray = Input(project_energy_discharged_kwh_5m),
        date_local_5m: xr.DataArray = Input(TransformBess.date_local_5m),
    ) -> xr.DataArray:
        """
        Use the sum of the 5-minute energy because the bexar meter accumulator rolls
        over several times in a single 24 hour period, making the last minus
        first approach unreliable.
        """
        return energy.groupby(date_local(date_local_5m)).sum()

    @method_calc
    @override
    def project_energy_charged_kwh_d(
        energy: xr.DataArray = Input(project_energy_charged_kwh_5m),
        date_local_5m: xr.DataArray = Input(TransformBess.date_local_5m),
    ) -> xr.DataArray:
        """
        Use the sum of the 5-minute energy because the bexar meter accumulator rolls
        over several times in a single 24 hour period, making the last minus
        first approach unreliable.
        """
        return energy.groupby(date_local(date_local_5m)).sum()

    @method_calc
    @override
    def project_aux_energy_kwh_d(
        energy_total: xr.DataArray = Input(
            TransformBess.project_total_aux_energy_filled_kwh_5m
        ),
        power_capacity: xr.DataArray = Input(
            TransformBess.project_power_capacity_kw
        ),
        date_local_5m: xr.DataArray = Input(TransformBess.date_local_5m),
    ) -> xr.DataArray:
        """
        Include 16-bit integer overflow handling.
        """
        return daily_energy(
            total_energy_5m=energy_total,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
            max_capacity_factor=24 * 0.1,
            modulus=65_536,
        )

    @method_calc
    @override
    def circuit_energy_charged_kwh_d(
        energy_total: xr.DataArray = Input(
            TransformBess.circuit_total_energy_charged_filled_kwh_5m
        ),
        power_capacity: xr.DataArray = Input(
            TransformBess.circuit_power_capacity_kw
        ),
        date_local_5m: xr.DataArray = Input(TransformBess.date_local_5m),
    ) -> xr.DataArray:
        return daily_energy(
            total_energy_5m=energy_total,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
            modulus=65_536,
        )

    @method_calc
    @override
    def circuit_energy_discharged_kwh_d(
        energy_total: xr.DataArray = Input(
            TransformBess.circuit_total_energy_discharged_filled_kwh_5m
        ),
        power_capacity: xr.DataArray = Input(
            TransformBess.circuit_power_capacity_kw
        ),
        date_local_5m: xr.DataArray = Input(TransformBess.date_local_5m),
    ) -> xr.DataArray:
        return daily_energy(
            total_energy_5m=energy_total,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
            modulus=65_536,
        )

    @method_calc
    @override
    def string_energy_charged_kwh_d(
        energy_total: xr.DataArray = Input(
            TransformBess.string_total_energy_charged_filled_kwh_5m
        ),
        power_capacity: xr.DataArray = Input(
            TransformBess.string_power_capacity_kw
        ),
        date_local_5m: xr.DataArray = Input(TransformBess.date_local_5m),
    ) -> xr.DataArray:
        return daily_energy(
            total_energy_5m=energy_total,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
            modulus=6_553.6,
        )

    @method_calc
    @override
    def string_energy_discharged_kwh_d(
        energy_total: xr.DataArray = Input(
            TransformBess.string_total_energy_discharged_filled_kwh_5m
        ),
        power_capacity: xr.DataArray = Input(
            TransformBess.string_power_capacity_kw
        ),
        date_local_5m: xr.DataArray = Input(TransformBess.date_local_5m),
    ) -> xr.DataArray:
        return daily_energy(
            total_energy_5m=energy_total,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
            modulus=6_553.6,
        )
