from typing import override

import xarray as xr
from kpi.base.enumeration import TimeCoords
from kpi.base.protocol import CalcProtocol
from kpi.domain.util import date_local, diff, filter_mask
from kpi.op.field import MakeField
from kpi.op.transform.class_calc import DailyEnergy
from kpi.op.transform.method import method_calc, required
from kpi.registry.transform.bess.api import TransformBess
from kpi.registry.transform.pv.api import Transform

field = MakeField[CalcProtocol].infer_doc


class BexarTransform(Transform):
    allow_override = True

    @method_calc
    @override
    def project_energy_charged_kwh_5m(
        energy_total: xr.DataArray = required(
            TransformBess.project_total_energy_charged_filled_kwh_5m
        ),
        power_capacity: xr.DataArray = required(Transform.project_power_capacity_kw),
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
        energy_total: xr.DataArray = required(
            TransformBess.project_total_energy_discharged_filled_kwh_5m
        ),
        power_capacity: xr.DataArray = required(
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
        energy: xr.DataArray = required(project_energy_discharged_kwh_5m),
        date_local_5m: xr.DataArray = required(TransformBess.date_local_5m),
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
        energy: xr.DataArray = required(project_energy_charged_kwh_5m),
        date_local_5m: xr.DataArray = required(TransformBess.date_local_5m),
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
        total_energy_5m: xr.DataArray = required(
            TransformBess.project_total_aux_energy_filled_kwh_5m
        ),
        power_capacity: xr.DataArray = required(
            TransformBess.project_power_capacity_kw
        ),
        date_local_5m: xr.DataArray = required(TransformBess.date_local_5m),
    ) -> xr.DataArray:
        """
        Project Auxiliary Energy Per Day
        Takes the accumulator differences between midnight and midnight the next day
        and filters out any negatives values or days where the aux energy is greater
        than the equivalent of 24 hours of 10% of the project's power capacity.
        Include 16-bit integer overflow handling.
        """
        total_energy_d = total_energy_5m.groupby(date_local(date_local_5m)).first()
        difference = diff(total_energy_d, time_dim=TimeCoords.DATE_LOCAL)
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

    circuit_energy_charged_kwh_d = field(
        DailyEnergy(
            total_energy_5m=TransformBess.circuit_total_energy_charged_filled_kwh_5m,
            energy_capacity=TransformBess.circuit_energy_capacity_kwh,
            date_local_5m=TransformBess.date_local_5m,
            modulus=65_536,
        )
    )

    circuit_energy_discharged_kwh_d = field(
        DailyEnergy(
            total_energy_5m=TransformBess.circuit_total_energy_discharged_filled_kwh_5m,
            energy_capacity=TransformBess.circuit_energy_capacity_kwh,
            date_local_5m=TransformBess.date_local_5m,
            modulus=65_536,
        )
    )

    string_energy_charged_kwh_d = field(
        DailyEnergy(
            total_energy_5m=TransformBess.string_total_energy_charged_filled_kwh_5m,
            energy_capacity=TransformBess.string_energy_capacity_kwh,
            date_local_5m=TransformBess.date_local_5m,
            modulus=6_553.6,
        )
    )

    string_energy_discharged_kwh_d = field(
        DailyEnergy(
            total_energy_5m=TransformBess.string_total_energy_discharged_filled_kwh_5m,
            energy_capacity=TransformBess.string_energy_capacity_kwh,
            date_local_5m=TransformBess.date_local_5m,
            modulus=6_553.6,
        )
    )
