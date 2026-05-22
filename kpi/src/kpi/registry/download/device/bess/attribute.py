from core.enumerations import DeviceTypeEnum

from core import models
from kpi.base.protocol import DeviceProtocol
from kpi.op.download.device.attribute import device_attribute_field
from kpi.op.field_registry import FieldRegistry


class DownloadDeviceBessAttribute(FieldRegistry[DeviceProtocol]):
    # =======================================================
    # Capacity
    # =======================================================

    # mv circuit

    circuit_energy_capacity_raw_kwh = device_attribute_field(
        device_type=DeviceTypeEnum.BESS_MV_COLLECTOR_CIRCUIT_METER,
        source_field_name=models.Device.capacity_energy_dc.name,
    )

    # pcs

    pcs_energy_capacity_raw_kwh = device_attribute_field(
        device_type=DeviceTypeEnum.BESS_PCS,
        source_field_name=models.Device.capacity_energy_dc.name,
    )

    pcs_power_capacity_raw_kw = device_attribute_field(
        device_type=DeviceTypeEnum.BESS_PCS,
        source_field_name=models.Device.capacity_ac.name,
    )

    # pcs module

    pcs_module_energy_capacity_raw_kwh = device_attribute_field(
        device_type=DeviceTypeEnum.BESS_PCS_MODULE,
        source_field_name=models.Device.capacity_energy_dc.name,
    )

    # string

    string_power_capacity_raw_kw = device_attribute_field(
        device_type=DeviceTypeEnum.BESS_STRING,
        source_field_name=models.Device.capacity_dc.name,
    )

    string_energy_capacity_raw_kwh = device_attribute_field(
        device_type=DeviceTypeEnum.BESS_STRING,
        source_field_name=models.Device.capacity_energy_dc.name,
    )
