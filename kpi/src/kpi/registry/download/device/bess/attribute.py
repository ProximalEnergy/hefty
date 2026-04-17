from core.enumerations import DeviceType
from kpi.op.download.device.attribute import device_attribute_field
from kpi.op.download.device.schema import DeviceSchema

from core import models

field = device_attribute_field


class DownloadDeviceBessAttribute(DeviceSchema):
    # =======================================================
    # Capacity
    # =======================================================

    # mv circuit

    circuit_power_capacity_raw_kw = field(
        device_type=DeviceType.BESS_MV_COLLECTOR_CIRCUIT_METER,
        source_field_name=models.Device.capacity_ac.name,
    )

    # pcs

    pcs_energy_capacity_raw_kwh = field(
        device_type=DeviceType.BESS_PCS,
        source_field_name=models.Device.capacity_dc.name,
    )

    pcs_power_capacity_raw_kw = field(
        device_type=DeviceType.BESS_PCS,
        source_field_name=models.Device.capacity_ac.name,
    )

    # pcs module

    pcs_module_power_capacity_raw_kw = field(
        device_type=DeviceType.BESS_PCS_MODULE,
        source_field_name=models.Device.capacity_ac.name,
    )

    # string

    string_power_capacity_raw_kw = field(
        device_type=DeviceType.BESS_STRING,
        source_field_name=models.Device.capacity_ac.name,
    )

    string_energy_capacity_raw_kwh = field(
        device_type=DeviceType.BESS_STRING,
        source_field_name=models.Device.capacity_dc.name,
    )
