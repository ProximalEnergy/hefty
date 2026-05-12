"""
Energy-based kpis including energy charged, energy discharged, aux, and RTE
"""

import xarray as xr
from core.enumerations import DeviceTypeEnum
from kpi.base.protocol import CalcProtocol
from kpi.domain.agg.across_devices import sum_across_devices
from kpi.domain.bess import (
    bess_filter_daily_energy,
    energy_efficiency,
    maximum_continuous_discharged_energy,
)
from kpi.domain.util import filter_mask
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
    string_energy_charged_kwh_d = calc_field(bess_filter_daily_energy)(
        energy_unfiltered_d=Required(Eval.string_energy_charged_unfiltered_kwh_d),
        energy_capacity=Required(Clean.string_energy_capacity_kwh),
    )

    project_string_energy_charged_kwh_d = calc_field(sum_across_devices)(
        Required(string_energy_charged_kwh_d),
        device_type=Constant(DeviceTypeEnum.BESS_STRING),
    )

    # BESS_STRING_ENERGY_DISCHARGED (41)

    string_energy_discharged_kwh_d = calc_field(bess_filter_daily_energy)(
        energy_unfiltered_d=Required(Eval.string_energy_discharged_unfiltered_kwh_d),
        energy_capacity=Required(Clean.string_energy_capacity_kwh),
    )

    project_string_energy_discharged_kwh_d = calc_field(sum_across_devices)(
        Required(string_energy_discharged_kwh_d),
        device_type=Constant(DeviceTypeEnum.BESS_STRING),
    )

    # =======================================================
    # PCS Module level
    # =======================================================

    # BESS_PCS_MODULE_ENERGY_CHARGED (113)

    pcs_module_energy_charged_kwh_d = calc_field(bess_filter_daily_energy)(
        energy_unfiltered_d=Required(Eval.pcs_module_energy_charged_unfiltered_kwh_d),
        energy_capacity=Required(Clean.pcs_module_energy_capacity_kwh),
    )

    project_pcs_module_energy_charged_kwh_d = calc_field(sum_across_devices)(
        Required(pcs_module_energy_charged_kwh_d),
        device_type=Constant(DeviceTypeEnum.BESS_PCS_MODULE),
    )

    # BESS_PCS_MODULE_ENERGY_DISCHARGED (114)

    pcs_module_energy_discharged_kwh_d = calc_field(bess_filter_daily_energy)(
        energy_unfiltered_d=Required(
            Eval.pcs_module_energy_discharged_unfiltered_kwh_d
        ),
        energy_capacity=Required(Clean.pcs_module_energy_capacity_kwh),
    )

    project_pcs_module_energy_discharged_kwh_d = calc_field(sum_across_devices)(
        Required(pcs_module_energy_discharged_kwh_d),
        device_type=Constant(DeviceTypeEnum.BESS_PCS_MODULE),
    )

    # =======================================================
    # PCS level
    # =======================================================

    # BESS_PCS_ENERGY_CHARGED_DC (87)
    pcs_energy_charged_dc_kwh_d = calc_field(bess_filter_daily_energy)(
        energy_unfiltered_d=Required(Eval.pcs_energy_charged_dc_unfiltered_kwh_d),
        energy_capacity=Required(Clean.pcs_energy_capacity_kwh),
    )

    project_pcs_energy_charged_dc_kwh_d = calc_field(sum_across_devices)(
        Required(pcs_energy_charged_dc_kwh_d),
        device_type=Constant(DeviceTypeEnum.BESS_PCS),
    )

    # BESS_PCS_ENERGY_DISCHARGED_DC (88)
    pcs_energy_discharged_dc_kwh_d = calc_field(bess_filter_daily_energy)(
        energy_unfiltered_d=Required(Eval.pcs_energy_discharged_dc_unfiltered_kwh_d),
        energy_capacity=Required(Clean.pcs_energy_capacity_kwh),
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
    circuit_energy_charged_kwh_d = calc_field(bess_filter_daily_energy)(
        energy_unfiltered_d=Required(Eval.circuit_energy_charged_unfiltered_kwh_d),
        energy_capacity=Required(Clean.circuit_energy_capacity_kwh),
    )

    project_circuit_energy_charged_kwh_d = calc_field(sum_across_devices)(
        Required(circuit_energy_charged_kwh_d),
        device_type=Constant(DeviceTypeEnum.BESS_MV_COLLECTOR_CIRCUIT_METER),
    )

    # BESS_CIRCUIT_ENERGY_DISCHARGED (112)
    circuit_energy_discharged_kwh_d = calc_field(bess_filter_daily_energy)(
        energy_unfiltered_d=Required(Eval.circuit_energy_discharged_unfiltered_kwh_d),
        energy_capacity=Required(Clean.circuit_energy_capacity_kwh),
    )

    project_circuit_energy_discharged_kwh_d = calc_field(sum_across_devices)(
        Required(circuit_energy_discharged_kwh_d),
        device_type=Constant(DeviceTypeEnum.BESS_MV_COLLECTOR_CIRCUIT_METER),
    )

    # =======================================================
    # Project level
    # =======================================================

    # BESS_PROJECT_ENERGY_CHARGED (35)
    project_energy_charged_kwh_d = calc_field(bess_filter_daily_energy)(
        energy_unfiltered_d=Required(Eval.project_energy_charged_unfiltered_kwh_d),
        energy_capacity=Required(Clean.project_energy_capacity_kwh),
    )

    # PROJECT_ENERGY_DISCHARGED (39)
    project_energy_discharged_kwh_d = calc_field(bess_filter_daily_energy)(
        energy_unfiltered_d=Required(Eval.project_energy_discharged_unfiltered_kwh_d),
        energy_capacity=Required(Clean.project_energy_capacity_kwh),
    )

    # BESS_MV_AUX_METER_ENERGY (93)
    @method_calc(
        energy_unfiltered_d=Required(Eval.project_aux_energy_unfiltered_kwh_d),
        power_capacity=Required(Clean.project_power_capacity_kw),
    )
    def project_aux_energy_kwh_d(
        energy_unfiltered_d: xr.DataArray,
        power_capacity: xr.DataArray,
    ) -> xr.DataArray:
        """
        Project Auxiliary Energy Per Day
        Filters out any negative values or days where the aux energy is greater
        than the equivalent of 24 hours of 10% of the project's power capacity.
        """
        epsilon = 1e-6
        return energy_unfiltered_d.where(
            filter_mask(
                filter_by=energy_unfiltered_d / power_capacity,
                min_value=-epsilon,
                max_value=24 * 0.1,
            ),
        )

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
