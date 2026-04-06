from kpi.domain.util import verify_positive
from kpi.service.transform.schema import CalcSchema
from kpi.service.transform.unary import unary_field
from kpi.workflow.download.device.bess.attribute import (
    DownloadDeviceBessAttribute,
)

T = DownloadDeviceBessAttribute


class TransformBessCleanDeviceAttribute(CalcSchema):
    # mv circuit

    circuit_power_capacity_kw = unary_field(
        verify_positive,
        field=T.circuit_power_capacity_raw_kw,
    )

    # pcs

    pcs_energy_capacity_kwh = unary_field(
        verify_positive,
        field=T.pcs_energy_capacity_raw_kwh,
    )

    pcs_power_capacity_kw = unary_field(
        verify_positive,
        field=T.pcs_power_capacity_raw_kw,
    )

    # pcs module

    pcs_module_energy_capacity_kwh = unary_field(
        verify_positive,
        field=T.pcs_module_energy_capacity_raw_kwh,
    )

    pcs_module_power_capacity_kw = unary_field(
        verify_positive,
        field=T.pcs_module_power_capacity_raw_kw,
    )

    # string

    string_power_capacity_kw = unary_field(
        verify_positive,
        field=T.string_power_capacity_raw_kw,
    )

    string_energy_capacity_kwh = unary_field(
        verify_positive,
        field=T.string_energy_capacity_raw_kwh,
    )
