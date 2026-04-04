"""
Energy-based kpis including energy charged, energy discharged, aux, and RTE
"""

import xarray as xr
from core.enumerations import DeviceType
from kpi.base.enumeration import TimeCoords
from kpi.base.util import coord
from kpi.domain.bess import daily_energy
from kpi.domain.util import cumsum, date_local, filter_mask
from kpi.service.transform.method import Input, method_calc
from kpi.service.transform.schema import CalcSchema
from kpi.workflow.transform.bess.clean.workflow import TransformBessClean as Clean
from kpi.workflow.transform.bess.evaluate.evaluate import TransformBessEvaluate as Eval


class TransformBessSummarizeEnergy(CalcSchema):
    # =======================================================
    # String level
    # =======================================================

    # BESS_STRING_ENERGY_CHARGED (37)
    @method_calc
    def string_energy_charged_kwh_d(
        total_energy: xr.DataArray = Input(
            Eval.string_total_energy_charged_filled_kwh_5m.name
        ),
        power_capacity: xr.DataArray = Input(Clean.string_power_capacity_kw.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return daily_energy(
            total_energy_5m=total_energy,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
        )

    @method_calc
    def project_string_energy_charged_kwh_d(
        energy: xr.DataArray = Input(string_energy_charged_kwh_d.name),
    ) -> xr.DataArray:
        return energy.sum(dim=coord(DeviceType.BESS_STRING), min_count=1)

    # BESS_STRING_ENERGY_DISCHARGED (41)

    @method_calc
    def string_energy_discharged_kwh_d(
        total_energy: xr.DataArray = Input(
            Eval.string_total_energy_discharged_filled_kwh_5m.name
        ),
        power_capacity: xr.DataArray = Input(Clean.string_power_capacity_kw.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return daily_energy(
            total_energy_5m=total_energy,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
        )

    @method_calc
    def project_string_energy_discharged_kwh_d(
        energy: xr.DataArray = Input(string_energy_discharged_kwh_d.name),
    ) -> xr.DataArray:
        return energy.sum(dim=coord(DeviceType.BESS_STRING), min_count=1)

    # =======================================================
    # PCS Module level
    # =======================================================

    # BESS_PCS_MODULE_ENERGY_CHARGED (113)

    @method_calc
    def pcs_module_energy_charged_kwh_d(
        total_energy: xr.DataArray = Input(
            Eval.pcs_module_total_energy_charged_filled_kwh_5m.name
        ),
        power_capacity: xr.DataArray = Input(Clean.pcs_module_power_capacity_kw.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return daily_energy(
            total_energy_5m=total_energy,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
        )

    @method_calc
    def project_pcs_module_energy_charged_kwh_d(
        energy: xr.DataArray = Input(pcs_module_energy_charged_kwh_d.name),
    ) -> xr.DataArray:
        return energy.sum(dim=coord(DeviceType.BESS_PCS_MODULE), min_count=1)

    # BESS_PCS_MODULE_ENERGY_DISCHARGED (114)

    @method_calc
    def pcs_module_energy_discharged_kwh_d(
        total_energy: xr.DataArray = Input(
            Eval.pcs_module_total_energy_discharged_filled_kwh_5m.name
        ),
        power_capacity: xr.DataArray = Input(Clean.pcs_module_power_capacity_kw.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return daily_energy(
            total_energy_5m=total_energy,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
        )

    @method_calc
    def project_pcs_module_energy_discharged_kwh_d(
        energy: xr.DataArray = Input(pcs_module_energy_discharged_kwh_d.name),
    ) -> xr.DataArray:
        return energy.sum(dim=coord(DeviceType.BESS_PCS_MODULE), min_count=1)

    # =======================================================
    # PCS level
    # =======================================================

    # BESS_PCS_ENERGY_CHARGED_DC (87)
    @method_calc
    def pcs_energy_charged_dc_kwh_d(
        total_energy: xr.DataArray = Input(
            Eval.pcs_total_energy_charged_filled_kwh_5m.name
        ),
        power_capacity: xr.DataArray = Input(Clean.pcs_power_capacity_kw.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return daily_energy(
            total_energy_5m=total_energy,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
        )

    @method_calc
    def project_pcs_energy_charged_dc_kwh_d(
        energy: xr.DataArray = Input(pcs_energy_charged_dc_kwh_d.name),
    ) -> xr.DataArray:
        return energy.sum(dim=coord(DeviceType.BESS_PCS), min_count=1)

    # BESS_PCS_ENERGY_DISCHARGED_DC (88)
    @method_calc
    def pcs_energy_discharged_dc_kwh_d(
        total_energy: xr.DataArray = Input(
            Eval.pcs_total_energy_discharged_filled_kwh_5m.name
        ),
        power_capacity: xr.DataArray = Input(Clean.pcs_power_capacity_kw.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return daily_energy(
            total_energy_5m=total_energy,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
        )

    @method_calc
    def project_pcs_energy_discharged_dc_kwh_d(
        energy: xr.DataArray = Input(pcs_energy_discharged_dc_kwh_d.name),
    ) -> xr.DataArray:
        return energy.sum(dim=coord(DeviceType.BESS_PCS), min_count=1)

    # =======================================================
    # Circuit level
    # =======================================================

    # BESS_CIRCUIT_ENERGY_CHARGED (111)
    @method_calc
    def circuit_energy_charged_kwh_d(
        total_energy: xr.DataArray = Input(
            Eval.circuit_total_energy_charged_filled_kwh_5m.name
        ),
        power_capacity: xr.DataArray = Input(Clean.circuit_power_capacity_kw.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return daily_energy(
            total_energy_5m=total_energy,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
        )

    @method_calc
    def project_circuit_energy_charged_kwh_d(
        energy: xr.DataArray = Input(circuit_energy_charged_kwh_d.name),
    ) -> xr.DataArray:
        return energy.sum(dim=coord(DeviceType.BESS_MV_CIRCUIT_METER), min_count=1)

    # BESS_CIRCUIT_ENERGY_DISCHARGED (112)
    @method_calc
    def circuit_energy_discharged_kwh_d(
        total_energy: xr.DataArray = Input(
            Eval.circuit_total_energy_discharged_filled_kwh_5m.name
        ),
        power_capacity: xr.DataArray = Input(Clean.circuit_power_capacity_kw.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return daily_energy(
            total_energy_5m=total_energy,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
        )

    @method_calc
    def project_circuit_energy_discharged_kwh_d(
        energy: xr.DataArray = Input(circuit_energy_discharged_kwh_d.name),
    ) -> xr.DataArray:
        return energy.sum(dim=coord(DeviceType.BESS_MV_CIRCUIT_METER), min_count=1)

    # =======================================================
    # Project level
    # =======================================================

    # BESS_PROJECT_ENERGY_CHARGED (35)
    @method_calc
    def project_energy_charged_kwh_d(
        total_energy: xr.DataArray = Input(
            Eval.project_total_energy_charged_filled_kwh_5m.name
        ),
        power_capacity: xr.DataArray = Input(Clean.project_power_capacity_kw.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        # charging at full power for 12 hours
        return daily_energy(
            total_energy_5m=total_energy,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
        )

    # PROJECT_ENERGY_DISCHARGED (39)
    @method_calc
    def project_energy_discharged_kwh_d(
        total_energy: xr.DataArray = Input(
            Eval.project_total_energy_discharged_filled_kwh_5m.name
        ),
        power_capacity: xr.DataArray = Input(Clean.project_power_capacity_kw.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        # discharging at full power for 12 hours
        return daily_energy(
            total_energy_5m=total_energy,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
        )

    # BESS_MV_AUX_METER_ENERGY (93)
    @method_calc
    def project_aux_energy_kwh_d(
        total_energy: xr.DataArray = Input(
            Eval.project_total_aux_energy_filled_kwh_5m.name
        ),
        power_capacity: xr.DataArray = Input(Clean.project_power_capacity_kw.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        # 10% aux power all day
        return daily_energy(
            total_energy_5m=total_energy,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
            max_capacity_factor=24 * 0.1,
        )

    # BESS_PROJECT_ENERGY_CHARGED_NO_AUX (115)
    @method_calc
    def project_energy_charged_no_aux_kwh_d(
        energy_charged: xr.DataArray = Input(project_energy_charged_kwh_d.name),
        aux_energy: xr.DataArray = Input(project_aux_energy_kwh_d.name),
    ) -> xr.DataArray:
        return energy_charged - aux_energy

    # BESS_PROJECT_METER_TO_PCS_MODULE_CHARGE_EFFICIENCY (116)

    @method_calc
    def project_pcs_module_charge_efficiency_d(
        source: xr.DataArray = Input(project_energy_charged_kwh_d.name),
        sink: xr.DataArray = Input(project_pcs_module_energy_charged_kwh_d.name),
        energy_capacity: xr.DataArray = Input(Clean.project_energy_capacity_kwh.name),
    ) -> xr.DataArray:
        source_filtered = source.where(source / energy_capacity > 0.1)
        efficiency = source_filtered / sink
        epsilon = 1e-6
        return efficiency.where(
            filter_mask(filter_by=efficiency, min_value=0, max_value=1 + epsilon)
        )

    # BESS_PROJECT_PCS_MODULE_TO_METER_DISCHARGE_EFFICIENCY (117)
    @method_calc
    def project_pcs_module_discharge_efficiency_d(
        source: xr.DataArray = Input(project_pcs_module_energy_discharged_kwh_d.name),
        sink: xr.DataArray = Input(project_energy_discharged_kwh_d.name),
        energy_capacity: xr.DataArray = Input(Clean.project_energy_capacity_kwh.name),
    ) -> xr.DataArray:
        source_filtered = source.where(source / energy_capacity > 0.1)
        efficiency = source_filtered / sink
        epsilon = 1e-6
        return efficiency.where(
            filter_mask(filter_by=efficiency, min_value=0, max_value=1 + epsilon)
        )

    # PROJECT_MAXIMUM_CONTINUOUS_DISCHARGED_ENERGY (106)
    @method_calc
    def project_maximum_continuous_discharged_energy_kwh_d(
        discharge_5m: xr.DataArray = Input(Eval.project_energy_discharged_kwh_5m.name),
        charge_5m: xr.DataArray = Input(Eval.project_energy_charged_kwh_5m.name),
        energy_capacity: xr.DataArray = Input(Clean.project_energy_capacity_kwh.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        epsilon = 1e-6

        discharge_total = cumsum(discharge_5m)

        discharge_total_while_charging = discharge_total.where(charge_5m > epsilon)

        # determine a baseline total from the most recent charging event
        total_discharged_since_last_charging = discharge_total_while_charging.ffill(
            dim=TimeCoords.TIME_5MIN_UTC.value
        ).fillna(discharge_5m.min())

        total_discharged_during_discharging_event = (
            discharge_total - total_discharged_since_last_charging
        )

        # make sure the total discharged is not greater than the energy capacity
        filtered = total_discharged_during_discharging_event.where(
            filter_mask(
                filter_by=total_discharged_during_discharging_event / energy_capacity,
                min_value=0,
                max_value=1,
            )
        )

        return filtered.groupby(date_local(date_local_5m)).max()
