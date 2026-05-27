"""
Energy-based kpis including energy charged, energy discharged, aux, and RTE
"""

import xarray as xr
from core.enumerations import DeviceTypeEnum

from kpi.domain.agg.across_devices import sum_across_devices
from kpi.domain.bess import (
    bess_filter_daily_energy,
    energy_efficiency,
    maximum_continuous_discharged_energy,
)
from kpi.domain.util import filter_mask
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.arg import DeviceTypeConstant, grouper, optional, required
from kpi.op.transform.method import MethodCalc, calc_field
from kpi.registry.transform.bess.clean.api import TransformBessClean as Clean
from kpi.registry.transform.bess.evaluate.api import TransformBessEvaluate as Eval


def project_aux_energy_kwh_d(
    *,
    energy_unfiltered_d: xr.DataArray,
    power_capacity: xr.DataArray,
    max_aux_specific_yield: float = 24 * 0.1,
) -> xr.DataArray:
    """Filter daily auxiliary energy to plausible bounds.

    Filters negative values and days where aux energy exceeds
    ``max_aux_specific_yield`` times power capacity.

    Args:
        energy_unfiltered_d: Unfiltered daily auxiliary energy.
        power_capacity: Project power capacity for normalization.
        max_aux_specific_yield: Upper bound on aux energy per unit capacity.

    Returns:
        Filtered daily auxiliary energy.
    """
    epsilon = 1e-06
    return energy_unfiltered_d.where(
        filter_mask(
            filter_by=energy_unfiltered_d / power_capacity,
            min_value=-epsilon,
            max_value=max_aux_specific_yield,
        )
    )


def project_energy_charged_no_aux_kwh_d(
    *, energy_charged: xr.DataArray, aux_energy: xr.DataArray
) -> xr.DataArray:
    """Daily charged energy excluding auxiliary consumption.

    Args:
        energy_charged: Daily energy charged.
        aux_energy: Daily auxiliary energy.

    Returns:
        ``energy_charged - aux_energy``.
    """
    return energy_charged - aux_energy


class TransformBessSummarizeEnergy(FieldRegistry[MethodCalc]):
    # =======================================================
    # String level
    # =======================================================

    # BESS_STRING_ENERGY_CHARGED (37)
    string_energy_charged_kwh_d = calc_field(bess_filter_daily_energy)(
        energy_unfiltered_d=required(Eval.string_energy_charged_unfiltered_kwh_d),
        energy_capacity=required(Clean.string_energy_capacity_kwh),
    )

    project_string_energy_charged_kwh_d = calc_field(sum_across_devices)(
        required(string_energy_charged_kwh_d),
        device_type=DeviceTypeConstant(value=DeviceTypeEnum.BESS_STRING),
    )

    # BESS_STRING_ENERGY_DISCHARGED (41)

    string_energy_discharged_kwh_d = calc_field(bess_filter_daily_energy)(
        energy_unfiltered_d=required(Eval.string_energy_discharged_unfiltered_kwh_d),
        energy_capacity=required(Clean.string_energy_capacity_kwh),
    )

    project_string_energy_discharged_kwh_d = calc_field(sum_across_devices)(
        required(string_energy_discharged_kwh_d),
        device_type=DeviceTypeConstant(value=DeviceTypeEnum.BESS_STRING),
    )

    # =======================================================
    # PCS Module level
    # =======================================================

    # BESS_PCS_MODULE_ENERGY_CHARGED (113)

    pcs_module_energy_charged_kwh_d = calc_field(bess_filter_daily_energy)(
        energy_unfiltered_d=required(Eval.pcs_module_energy_charged_unfiltered_kwh_d),
        energy_capacity=required(Clean.pcs_module_energy_capacity_kwh),
    )

    project_pcs_module_energy_charged_kwh_d = calc_field(sum_across_devices)(
        required(pcs_module_energy_charged_kwh_d),
        device_type=DeviceTypeConstant(value=DeviceTypeEnum.BESS_PCS_MODULE),
    )

    # BESS_PCS_MODULE_ENERGY_DISCHARGED (114)

    pcs_module_energy_discharged_kwh_d = calc_field(bess_filter_daily_energy)(
        energy_unfiltered_d=required(
            Eval.pcs_module_energy_discharged_unfiltered_kwh_d
        ),
        energy_capacity=required(Clean.pcs_module_energy_capacity_kwh),
    )

    project_pcs_module_energy_discharged_kwh_d = calc_field(sum_across_devices)(
        required(pcs_module_energy_discharged_kwh_d),
        device_type=DeviceTypeConstant(value=DeviceTypeEnum.BESS_PCS_MODULE),
    )

    # =======================================================
    # PCS level
    # =======================================================

    # BESS_PCS_ENERGY_CHARGED_DC (87)
    pcs_energy_charged_dc_kwh_d = calc_field(bess_filter_daily_energy)(
        energy_unfiltered_d=required(Eval.pcs_energy_charged_dc_unfiltered_kwh_d),
        energy_capacity=required(Clean.pcs_energy_capacity_kwh),
    )

    project_pcs_energy_charged_dc_kwh_d = calc_field(sum_across_devices)(
        required(pcs_energy_charged_dc_kwh_d),
        device_type=DeviceTypeConstant(value=DeviceTypeEnum.BESS_PCS),
    )

    # BESS_PCS_ENERGY_DISCHARGED_DC (88)
    pcs_energy_discharged_dc_kwh_d = calc_field(bess_filter_daily_energy)(
        energy_unfiltered_d=required(Eval.pcs_energy_discharged_dc_unfiltered_kwh_d),
        energy_capacity=required(Clean.pcs_energy_capacity_kwh),
    )

    project_pcs_energy_discharged_dc_kwh_d = calc_field(sum_across_devices)(
        required(pcs_energy_discharged_dc_kwh_d),
        device_type=DeviceTypeConstant(value=DeviceTypeEnum.BESS_PCS),
    )

    pcs_maximum_continuous_discharged_energy_kwh_d = calc_field(
        maximum_continuous_discharged_energy
    )(
        discharge_energy=required(Eval.pcs_energy_discharged_kwh_5m),
        charge_energy=required(Eval.pcs_energy_charged_kwh_5m),
        energy_capacity=optional(Clean.pcs_energy_capacity_kwh),
        date_local_5m=grouper(Eval.date_local_5m),
    )

    project_pcs_maximum_continuous_discharged_energy_kwh_d = calc_field(
        maximum_continuous_discharged_energy
    )(
        discharge_energy=required(Eval.project_pcs_energy_discharged_kwh_5m),
        charge_energy=required(Eval.project_pcs_energy_charged_kwh_5m),
        energy_capacity=optional(Clean.project_energy_capacity_kwh),
        date_local_5m=grouper(Eval.date_local_5m),
    )

    # =======================================================
    # Circuit level
    # =======================================================

    # BESS_CIRCUIT_ENERGY_CHARGED (111)
    circuit_energy_charged_kwh_d = calc_field(bess_filter_daily_energy)(
        energy_unfiltered_d=required(Eval.circuit_energy_charged_unfiltered_kwh_d),
        energy_capacity=required(Clean.circuit_energy_capacity_kwh),
    )

    project_circuit_energy_charged_kwh_d = calc_field(sum_across_devices)(
        required(circuit_energy_charged_kwh_d),
        device_type=DeviceTypeConstant(
            value=DeviceTypeEnum.BESS_MV_COLLECTOR_CIRCUIT_METER
        ),
    )

    # BESS_CIRCUIT_ENERGY_DISCHARGED (112)
    circuit_energy_discharged_kwh_d = calc_field(bess_filter_daily_energy)(
        energy_unfiltered_d=required(Eval.circuit_energy_discharged_unfiltered_kwh_d),
        energy_capacity=required(Clean.circuit_energy_capacity_kwh),
    )

    project_circuit_energy_discharged_kwh_d = calc_field(sum_across_devices)(
        required(circuit_energy_discharged_kwh_d),
        device_type=DeviceTypeConstant(
            value=DeviceTypeEnum.BESS_MV_COLLECTOR_CIRCUIT_METER
        ),
    )

    # =======================================================
    # Project level
    # =======================================================

    # BESS_PROJECT_ENERGY_CHARGED (35)
    project_energy_charged_kwh_d = calc_field(bess_filter_daily_energy)(
        energy_unfiltered_d=required(Eval.project_energy_charged_unfiltered_kwh_d),
        energy_capacity=required(Clean.project_energy_capacity_kwh),
    )

    # PROJECT_ENERGY_DISCHARGED (39)
    project_energy_discharged_kwh_d = calc_field(bess_filter_daily_energy)(
        energy_unfiltered_d=required(Eval.project_energy_discharged_unfiltered_kwh_d),
        energy_capacity=required(Clean.project_energy_capacity_kwh),
    )

    # BESS_MV_AUX_METER_ENERGY (93)
    project_aux_energy_kwh_d = calc_field(project_aux_energy_kwh_d)(
        energy_unfiltered_d=required(Eval.project_aux_energy_unfiltered_kwh_d),
        power_capacity=required(Clean.project_power_capacity_kw),
    )

    # BESS_PROJECT_ENERGY_CHARGED_NO_AUX (115)
    project_energy_charged_no_aux_kwh_d = calc_field(
        project_energy_charged_no_aux_kwh_d
    )(
        energy_charged=required(project_energy_charged_kwh_d),
        aux_energy=required(project_aux_energy_kwh_d),
    )

    project_pcs_module_charge_efficiency_d = calc_field(energy_efficiency)(
        source=required(project_energy_charged_kwh_d),
        sink=required(project_pcs_module_energy_charged_kwh_d),
        energy_capacity=required(Clean.project_energy_capacity_kwh),
    )

    project_pcs_module_discharge_efficiency_d = calc_field(energy_efficiency)(
        source=required(project_pcs_module_energy_discharged_kwh_d),
        sink=required(project_energy_discharged_kwh_d),
        energy_capacity=required(Clean.project_energy_capacity_kwh),
    )

    # PROJECT_MAXIMUM_CONTINUOUS_DISCHARGED_ENERGY (106)
    project_maximum_continuous_discharged_energy_kwh_d = calc_field(
        maximum_continuous_discharged_energy
    )(
        discharge_energy=required(Eval.project_energy_discharged_kwh_5m),
        charge_energy=required(Eval.project_energy_charged_kwh_5m),
        energy_capacity=optional(Clean.project_energy_capacity_kwh),
        date_local_5m=grouper(Eval.date_local_5m),
    )
