"""
Energy-based kpis including energy charged, energy discharged, aux, and RTE
"""

import xarray as xr
from core.enumerations import DeviceType
from kpi.base.util import coord
from kpi.domain.bess import daily_energy, maximum_continuous_discharged_energy
from kpi.domain.util import filter_mask
from kpi.service.transform.method import Input, Optional, method_calc
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
            Eval.string_total_energy_charged_filled_kwh_5m
        ),
        power_capacity: xr.DataArray = Input(Clean.string_power_capacity_kw),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return daily_energy(
            total_energy_5m=total_energy,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
        )

    @method_calc
    def project_string_energy_charged_kwh_d(
        energy: xr.DataArray = Input(string_energy_charged_kwh_d),
    ) -> xr.DataArray:
        return energy.sum(dim=coord(DeviceType.BESS_STRING), min_count=1)

    # BESS_STRING_ENERGY_DISCHARGED (41)

    @method_calc
    def string_energy_discharged_kwh_d(
        total_energy: xr.DataArray = Input(
            Eval.string_total_energy_discharged_filled_kwh_5m
        ),
        power_capacity: xr.DataArray = Input(Clean.string_power_capacity_kw),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return daily_energy(
            total_energy_5m=total_energy,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
        )

    @method_calc
    def project_string_energy_discharged_kwh_d(
        energy: xr.DataArray = Input(string_energy_discharged_kwh_d),
    ) -> xr.DataArray:
        return energy.sum(dim=coord(DeviceType.BESS_STRING), min_count=1)

    # =======================================================
    # PCS Module level
    # =======================================================

    # BESS_PCS_MODULE_ENERGY_CHARGED (113)

    @method_calc
    def pcs_module_energy_charged_kwh_d(
        total_energy: xr.DataArray = Input(
            Eval.pcs_module_total_energy_charged_filled_kwh_5m
        ),
        power_capacity: xr.DataArray = Input(Clean.pcs_module_power_capacity_kw),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return daily_energy(
            total_energy_5m=total_energy,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
        )

    @method_calc
    def project_pcs_module_energy_charged_kwh_d(
        energy: xr.DataArray = Input(pcs_module_energy_charged_kwh_d),
    ) -> xr.DataArray:
        return energy.sum(dim=coord(DeviceType.BESS_PCS_MODULE), min_count=1)

    # BESS_PCS_MODULE_ENERGY_DISCHARGED (114)

    @method_calc
    def pcs_module_energy_discharged_kwh_d(
        total_energy: xr.DataArray = Input(
            Eval.pcs_module_total_energy_discharged_filled_kwh_5m
        ),
        power_capacity: xr.DataArray = Input(Clean.pcs_module_power_capacity_kw),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return daily_energy(
            total_energy_5m=total_energy,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
        )

    @method_calc
    def project_pcs_module_energy_discharged_kwh_d(
        energy: xr.DataArray = Input(pcs_module_energy_discharged_kwh_d),
    ) -> xr.DataArray:
        return energy.sum(dim=coord(DeviceType.BESS_PCS_MODULE), min_count=1)

    # =======================================================
    # PCS level
    # =======================================================

    # BESS_PCS_ENERGY_CHARGED_DC (87)
    @method_calc
    def pcs_energy_charged_dc_kwh_d(
        total_energy: xr.DataArray = Input(Eval.pcs_total_energy_charged_filled_kwh_5m),
        power_capacity: xr.DataArray = Input(Clean.pcs_power_capacity_kw),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return daily_energy(
            total_energy_5m=total_energy,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
        )

    @method_calc
    def project_pcs_energy_charged_dc_kwh_d(
        energy: xr.DataArray = Input(pcs_energy_charged_dc_kwh_d),
    ) -> xr.DataArray:
        return energy.sum(dim=coord(DeviceType.BESS_PCS), min_count=1)

    # BESS_PCS_ENERGY_DISCHARGED_DC (88)
    @method_calc
    def pcs_energy_discharged_dc_kwh_d(
        total_energy: xr.DataArray = Input(
            Eval.pcs_total_energy_discharged_filled_kwh_5m
        ),
        power_capacity: xr.DataArray = Input(Clean.pcs_power_capacity_kw),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return daily_energy(
            total_energy_5m=total_energy,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
        )

    @method_calc
    def project_pcs_energy_discharged_dc_kwh_d(
        energy: xr.DataArray = Input(pcs_energy_discharged_dc_kwh_d),
    ) -> xr.DataArray:
        return energy.sum(dim=coord(DeviceType.BESS_PCS), min_count=1)

    @method_calc
    def pcs_maximum_continuous_discharged_energy_kwh_d(
        discharge_5m: xr.DataArray = Input(Eval.pcs_energy_discharged_dc_kwh_5m),
        charge_5m: xr.DataArray = Input(Eval.pcs_energy_charged_dc_kwh_5m),
        energy_capacity: xr.DataArray | None = Optional(Clean.pcs_energy_capacity_kwh),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        """
        PCS Maximum Continuous Discharged Energy (kWh) Per Day
        Used to calculate `BESS_PCS_MAXIMUM_CONTINUOUS_DISCHARGED_ENERGY` (109).
        See `maximum_continuous_discharged_energy` for more details.
        """
        return maximum_continuous_discharged_energy(
            energy=discharge_5m - charge_5m,
            is_charging=charge_5m > 1e-6,
            energy_capacity=energy_capacity,
            date_local_5m=date_local_5m,
        )

    @method_calc
    def project_pcs_maximum_continuous_discharged_energy_kwh_d(
        pcs_discharge_5m: xr.DataArray = Input(Eval.pcs_energy_discharged_dc_kwh_5m),
        pcs_charge_5m: xr.DataArray = Input(Eval.pcs_energy_charged_dc_kwh_5m),
        project_charge_5m: xr.DataArray = Input(Eval.project_energy_charged_kwh_5m),
        energy_capacity: xr.DataArray = Input(Clean.project_energy_capacity_kwh),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        """
        Project PCS Maximum Continuous Discharged Energy (kWh) Per Day
        Used to calculate `BESS_PCS_MAXIMUM_CONTINUOUS_DISCHARGED_ENERGY` (109).
        PCS energy is summed across devices before determining the
        longest continuous discharging period.
        Since it's possible for some PCS's to be charging slightly while others
        discharge, the charging period is determined at the meter level.
        See `maximum_continuous_discharged_energy` for more details.
        """
        discharge = pcs_discharge_5m.sum(dim=coord(DeviceType.BESS_PCS), min_count=1)
        charge = pcs_charge_5m.sum(dim=coord(DeviceType.BESS_PCS), min_count=1)
        return maximum_continuous_discharged_energy(
            energy=discharge - charge,
            is_charging=project_charge_5m > 1e-6,
            energy_capacity=energy_capacity,
            date_local_5m=date_local_5m,
        )

    # =======================================================
    # Circuit level
    # =======================================================

    # BESS_CIRCUIT_ENERGY_CHARGED (111)
    @method_calc
    def circuit_energy_charged_kwh_d(
        total_energy: xr.DataArray = Input(
            Eval.circuit_total_energy_charged_filled_kwh_5m
        ),
        power_capacity: xr.DataArray = Input(Clean.circuit_power_capacity_kw),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return daily_energy(
            total_energy_5m=total_energy,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
        )

    @method_calc
    def project_circuit_energy_charged_kwh_d(
        energy: xr.DataArray = Input(circuit_energy_charged_kwh_d),
    ) -> xr.DataArray:
        return energy.sum(
            dim=coord(DeviceType.BESS_MV_COLLECTOR_CIRCUIT_METER), min_count=1
        )

    # BESS_CIRCUIT_ENERGY_DISCHARGED (112)
    @method_calc
    def circuit_energy_discharged_kwh_d(
        total_energy: xr.DataArray = Input(
            Eval.circuit_total_energy_discharged_filled_kwh_5m
        ),
        power_capacity: xr.DataArray = Input(Clean.circuit_power_capacity_kw),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return daily_energy(
            total_energy_5m=total_energy,
            power_capacity=power_capacity,
            date_local_5m=date_local_5m,
        )

    @method_calc
    def project_circuit_energy_discharged_kwh_d(
        energy: xr.DataArray = Input(circuit_energy_discharged_kwh_d),
    ) -> xr.DataArray:
        return energy.sum(
            dim=coord(DeviceType.BESS_MV_COLLECTOR_CIRCUIT_METER), min_count=1
        )

    # =======================================================
    # Project level
    # =======================================================

    # BESS_PROJECT_ENERGY_CHARGED (35)
    @method_calc
    def project_energy_charged_kwh_d(
        total_energy: xr.DataArray = Input(
            Eval.project_total_energy_charged_filled_kwh_5m
        ),
        power_capacity: xr.DataArray = Input(Clean.project_power_capacity_kw),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
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
            Eval.project_total_energy_discharged_filled_kwh_5m
        ),
        power_capacity: xr.DataArray = Input(Clean.project_power_capacity_kw),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
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
        total_energy: xr.DataArray = Input(Eval.project_total_aux_energy_filled_kwh_5m),
        power_capacity: xr.DataArray = Input(Clean.project_power_capacity_kw),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
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
        energy_charged: xr.DataArray = Input(project_energy_charged_kwh_d),
        aux_energy: xr.DataArray = Input(project_aux_energy_kwh_d),
    ) -> xr.DataArray:
        return energy_charged - aux_energy

    @method_calc
    def project_pcs_module_charge_efficiency_d(
        source: xr.DataArray = Input(project_energy_charged_kwh_d),
        sink: xr.DataArray = Input(project_pcs_module_energy_charged_kwh_d),
        energy_capacity: xr.DataArray = Input(Clean.project_energy_capacity_kwh),
    ) -> xr.DataArray:
        """
        Project PCS Module Charge Efficiency Per Day
        Used to calculate `BESS_PROJECT_METER_TO_PCS_MODULE_CHARGE_EFFICIENCY` (116).
        Total energy charged at the PCS module level divided by
        the energy charged at the meter. Days where the project
        charged less than 10% of the energy capacity are excluded.
        """
        source_filtered = source.where(source / energy_capacity > 0.1)
        efficiency = sink / source_filtered
        epsilon = 1e-6
        return efficiency.where(
            filter_mask(filter_by=efficiency, min_value=0, max_value=1 + epsilon)
        )

    @method_calc
    def project_pcs_module_discharge_efficiency_d(
        source: xr.DataArray = Input(project_pcs_module_energy_discharged_kwh_d),
        sink: xr.DataArray = Input(project_energy_discharged_kwh_d),
        energy_capacity: xr.DataArray = Input(Clean.project_energy_capacity_kwh),
    ) -> xr.DataArray:
        """
        Project PCS Module Discharge Efficiency Per Day
        Used to calculate `BESS_PROJECT_PCS_MODULE_TO_METER_DISCHARGE_EFFICIENCY` (117).
        Energy discharged at the meter divided by the total energy
        discharged at the PCS module level. Days where the project
        discharged less than 10% of the energy capacity
        (as measured by the PCS) are excluded.
        """
        source_filtered = source.where(source / energy_capacity > 0.1)
        efficiency = sink / source_filtered
        epsilon = 1e-6
        return efficiency.where(
            filter_mask(filter_by=efficiency, min_value=0, max_value=1 + epsilon)
        )

    # PROJECT_MAXIMUM_CONTINUOUS_DISCHARGED_ENERGY (106)
    @method_calc
    def project_maximum_continuous_discharged_energy_kwh_d(
        discharge_5m: xr.DataArray = Input(Eval.project_energy_discharged_kwh_5m),
        charge_5m: xr.DataArray = Input(Eval.project_energy_charged_kwh_5m),
        energy_capacity: xr.DataArray = Input(Clean.project_energy_capacity_kwh),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return maximum_continuous_discharged_energy(
            energy=discharge_5m - charge_5m,
            is_charging=charge_5m > 1e-6,
            energy_capacity=energy_capacity,
            date_local_5m=date_local_5m,
        )
