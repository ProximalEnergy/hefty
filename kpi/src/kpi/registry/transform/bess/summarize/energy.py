"""
Energy-based kpis including energy charged, energy discharged, aux, and RTE
"""

import xarray as xr
from core.enumerations import DeviceTypeEnum
from kpi.base.enumeration import TimeCoords
from kpi.base.protocol import CalcProtocol
from kpi.domain.agg.across_devices import sum_across_devices
from kpi.domain.bess import (
    daily_energy,
    energy_efficiency,
    maximum_continuous_discharged_energy,
)
from kpi.domain.util import diff, filter_mask, rename
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.arg import Constant, Optional, Required
from kpi.op.transform.method import calc_field, method_calc
from kpi.registry.transform.bess.clean.api import TransformBessClean as Clean
from kpi.registry.transform.bess.evaluate.api import TransformBessEvaluate as Eval


class TransformBessSummarizeEnergy(FieldRegistry[CalcProtocol]):
    # =======================================================
    # String level
    # =======================================================

    # BESS_STRING_ENERGY_CHARGED (37)
    string_energy_charged_kwh_d = calc_field(daily_energy)(
        total_energy_5m=Required(Eval.string_total_energy_charged_filled_kwh_5m),
        energy_capacity=Required(Clean.string_energy_capacity_kwh),
        date_local_5m=Required(Eval.date_local_5m),
    )

    project_string_energy_charged_kwh_d = calc_field(sum_across_devices)(
        Required(string_energy_charged_kwh_d),
        device_type=Constant(DeviceTypeEnum.BESS_STRING),
    )

    # BESS_STRING_ENERGY_DISCHARGED (41)

    string_energy_discharged_kwh_d = calc_field(daily_energy)(
        total_energy_5m=Required(Eval.string_total_energy_discharged_filled_kwh_5m),
        energy_capacity=Required(Clean.string_energy_capacity_kwh),
        date_local_5m=Required(Eval.date_local_5m),
    )

    project_string_energy_discharged_kwh_d = calc_field(sum_across_devices)(
        Required(string_energy_discharged_kwh_d),
        device_type=Constant(DeviceTypeEnum.BESS_STRING),
    )

    # =======================================================
    # PCS Module level
    # =======================================================

    # BESS_PCS_MODULE_ENERGY_CHARGED (113)

    pcs_module_energy_charged_kwh_d = calc_field(daily_energy)(
        total_energy_5m=Required(Eval.pcs_module_total_energy_charged_filled_kwh_5m),
        energy_capacity=Required(Clean.pcs_module_energy_capacity_kwh),
        date_local_5m=Required(Eval.date_local_5m),
    )

    project_pcs_module_energy_charged_kwh_d = calc_field(sum_across_devices)(
        Required(pcs_module_energy_charged_kwh_d),
        device_type=Constant(DeviceTypeEnum.BESS_PCS_MODULE),
    )

    # BESS_PCS_MODULE_ENERGY_DISCHARGED (114)

    pcs_module_energy_discharged_kwh_d = calc_field(daily_energy)(
        total_energy_5m=Required(Eval.pcs_module_total_energy_discharged_filled_kwh_5m),
        energy_capacity=Required(Clean.pcs_module_energy_capacity_kwh),
        date_local_5m=Required(Eval.date_local_5m),
    )

    project_pcs_module_energy_discharged_kwh_d = calc_field(sum_across_devices)(
        Required(pcs_module_energy_discharged_kwh_d),
        device_type=Constant(DeviceTypeEnum.BESS_PCS_MODULE),
    )

    # =======================================================
    # PCS level
    # =======================================================

    # BESS_PCS_ENERGY_CHARGED_DC (87)
    pcs_energy_charged_dc_kwh_d = calc_field(daily_energy)(
        total_energy_5m=Required(Eval.pcs_total_energy_charged_filled_kwh_5m),
        energy_capacity=Required(Clean.pcs_energy_capacity_kwh),
        date_local_5m=Required(Eval.date_local_5m),
    )

    project_pcs_energy_charged_dc_kwh_d = calc_field(sum_across_devices)(
        Required(pcs_energy_charged_dc_kwh_d),
        device_type=Constant(DeviceTypeEnum.BESS_PCS),
    )

    # BESS_PCS_ENERGY_DISCHARGED_DC (88)
    pcs_energy_discharged_dc_kwh_d = calc_field(daily_energy)(
        total_energy_5m=Required(Eval.pcs_total_energy_discharged_filled_kwh_5m),
        energy_capacity=Required(Clean.pcs_energy_capacity_kwh),
        date_local_5m=Required(Eval.date_local_5m),
    )

    project_pcs_energy_discharged_dc_kwh_d = calc_field(sum_across_devices)(
        Required(pcs_energy_discharged_dc_kwh_d),
        device_type=Constant(DeviceTypeEnum.BESS_PCS),
    )

    pcs_maximum_continuous_discharged_energy_kwh_d = calc_field(
        maximum_continuous_discharged_energy
    )(
        discharge_energy=Required(Eval.pcs_energy_discharged_kwh_5m),
        charge_energy=Required(Eval.pcs_energy_charged_kwh_5m),
        energy_capacity=Optional(Clean.pcs_energy_capacity_kwh),
        date_local_5m=Required(Eval.date_local_5m),
    )

    project_pcs_maximum_continuous_discharged_energy_kwh_d = calc_field(
        maximum_continuous_discharged_energy
    )(
        discharge_energy=Required(Eval.project_pcs_energy_discharged_kwh_5m),
        charge_energy=Required(Eval.project_pcs_energy_charged_kwh_5m),
        energy_capacity=Optional(Clean.project_energy_capacity_kwh),
        date_local_5m=Required(Eval.date_local_5m),
    )

    # =======================================================
    # Circuit level
    # =======================================================

    # BESS_CIRCUIT_ENERGY_CHARGED (111)
    circuit_energy_charged_kwh_d = calc_field(daily_energy)(
        total_energy_5m=Required(Eval.circuit_total_energy_charged_filled_kwh_5m),
        energy_capacity=Required(Clean.circuit_energy_capacity_kwh),
        date_local_5m=Required(Eval.date_local_5m),
    )

    project_circuit_energy_charged_kwh_d = calc_field(sum_across_devices)(
        Required(circuit_energy_charged_kwh_d),
        device_type=Constant(DeviceTypeEnum.BESS_MV_COLLECTOR_CIRCUIT_METER),
    )

    # BESS_CIRCUIT_ENERGY_DISCHARGED (112)
    circuit_energy_discharged_kwh_d = calc_field(daily_energy)(
        total_energy_5m=Required(Eval.circuit_total_energy_discharged_filled_kwh_5m),
        energy_capacity=Required(Clean.circuit_energy_capacity_kwh),
        date_local_5m=Required(Eval.date_local_5m),
    )

    project_circuit_energy_discharged_kwh_d = calc_field(sum_across_devices)(
        Required(circuit_energy_discharged_kwh_d),
        device_type=Constant(DeviceTypeEnum.BESS_MV_COLLECTOR_CIRCUIT_METER),
    )

    # =======================================================
    # Project level
    # =======================================================

    # BESS_PROJECT_ENERGY_CHARGED (35)
    project_energy_charged_kwh_d = calc_field(daily_energy)(
        total_energy_5m=Required(Eval.project_total_energy_charged_filled_kwh_5m),
        energy_capacity=Required(Clean.project_energy_capacity_kwh),
        date_local_5m=Required(Eval.date_local_5m),
    )

    # PROJECT_ENERGY_DISCHARGED (39)
    project_energy_discharged_kwh_d = calc_field(daily_energy)(
        total_energy_5m=Required(Eval.project_total_energy_discharged_filled_kwh_5m),
        energy_capacity=Required(Clean.project_energy_capacity_kwh),
        date_local_5m=Required(Eval.date_local_5m),
    )

    # BESS_MV_AUX_METER_ENERGY (93)
    @method_calc(
        total_energy_5m=Required(Eval.project_total_aux_energy_filled_kwh_5m),
        power_capacity=Required(Clean.project_power_capacity_kw),
        date_local_5m=Required(Eval.date_local_5m),
    )
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
        """
        total_energy_d = total_energy_5m.groupby(rename(date_local_5m)).first()
        difference = diff(total_energy_d, time_dim=TimeCoords.DATE_LOCAL)
        epsilon = 1e-6
        difference = difference.where(
            filter_mask(
                filter_by=difference / power_capacity,
                min_value=-epsilon,
                max_value=24 * 0.1,
            )
        )
        return difference

    # BESS_PROJECT_ENERGY_CHARGED_NO_AUX (115)
    @method_calc(
        energy_charged=Required(project_energy_charged_kwh_d),
        aux_energy=Required(project_aux_energy_kwh_d),
    )
    def project_energy_charged_no_aux_kwh_d(
        energy_charged: xr.DataArray,
        aux_energy: xr.DataArray,
    ) -> xr.DataArray:
        return energy_charged - aux_energy

    project_pcs_module_charge_efficiency_d = calc_field(energy_efficiency)(
        source=Required(project_energy_charged_kwh_d),
        sink=Required(project_pcs_module_energy_charged_kwh_d),
        energy_capacity=Required(Clean.project_energy_capacity_kwh),
    )

    project_pcs_module_discharge_efficiency_d = calc_field(energy_efficiency)(
        source=Required(project_pcs_module_energy_discharged_kwh_d),
        sink=Required(project_energy_discharged_kwh_d),
        energy_capacity=Required(Clean.project_energy_capacity_kwh),
    )

    # PROJECT_MAXIMUM_CONTINUOUS_DISCHARGED_ENERGY (106)
    project_maximum_continuous_discharged_energy_kwh_d = calc_field(
        maximum_continuous_discharged_energy
    )(
        discharge_energy=Required(Eval.project_energy_discharged_kwh_5m),
        charge_energy=Required(Eval.project_energy_charged_kwh_5m),
        energy_capacity=Optional(Clean.project_energy_capacity_kwh),
        date_local_5m=Required(Eval.date_local_5m),
    )
