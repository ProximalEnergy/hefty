from kpi.domain.util import verify_positive
from kpi.service.transform.schema import CalcSchema
from kpi.service.transform.unary import unary_field
from kpi.workflow.download.device_attribute.bess import DownloadDeviceAttributeBess

T = DownloadDeviceAttributeBess


class TransformBessCleanDeviceAttribute(CalcSchema):
    # mv circuit

    circuit_power_capacity_kw = unary_field(
        verify_positive,
        T.circuit_power_capacity_raw_kw.name,
    )

    # pcs

    pcs_energy_capacity_kwh = unary_field(
        verify_positive,
        T.pcs_energy_capacity_raw_kwh.name,
    )

    pcs_power_capacity_kw = unary_field(
        verify_positive, T.pcs_power_capacity_raw_kw.name
    )

    # pcs module

    pcs_module_energy_capacity_kwh = unary_field(
        verify_positive,
        T.pcs_module_energy_capacity_raw_kwh.name,
    )

    pcs_module_power_capacity_kw = unary_field(
        verify_positive,
        T.pcs_module_power_capacity_raw_kw.name,
    )

    # string

    string_power_capacity_kw = unary_field(
        verify_positive,
        T.string_power_capacity_raw_kw.name,
    )

    string_energy_capacity_kwh = unary_field(
        verify_positive,
        T.string_energy_capacity_raw_kwh.name,
    )
