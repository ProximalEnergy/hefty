from kpi.base.protocol import CalcProtocol
from kpi.domain.util import verify_positive
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.unary import unary_field
from kpi.registry.download.device.bess.attribute import (
    DownloadDeviceBessAttribute as Download,
)


class TransformBessCleanDeviceAttribute(FieldRegistry[CalcProtocol]):
    # mv circuit

    circuit_energy_capacity_kwh = unary_field(
        verify_positive,
        field=Download.circuit_energy_capacity_raw_kwh,
    )

    # pcs

    pcs_energy_capacity_kwh = unary_field(
        verify_positive,
        field=Download.pcs_energy_capacity_raw_kwh,
    )

    pcs_power_capacity_kw = unary_field(
        verify_positive,
        field=Download.pcs_power_capacity_raw_kw,
    )

    # pcs module

    pcs_module_energy_capacity_kwh = unary_field(
        verify_positive,
        field=Download.pcs_module_energy_capacity_raw_kwh,
    )

    # string

    string_power_capacity_kw = unary_field(
        verify_positive,
        field=Download.string_power_capacity_raw_kw,
    )

    string_energy_capacity_kwh = unary_field(
        verify_positive,
        field=Download.string_energy_capacity_raw_kwh,
    )
