from core.enumerations import DeviceTypeEnum

from core import models
from kpi.base.protocol import DeviceProtocol
from kpi.op.download.device.attribute import (
    device_attribute_field,
)
from kpi.op.field_registry import FieldRegistry


class DownloadDevicePvAttribute(FieldRegistry[DeviceProtocol]):
    combiner_dc_capacity_raw_kw = device_attribute_field(
        device_type=DeviceTypeEnum.PV_DC_COMBINER,
        source_field_name=models.Device.capacity_dc.name,
    )

    inverter_ac_capacity_raw_kw = device_attribute_field(
        device_type=DeviceTypeEnum.PV_INVERTER,
        source_field_name=models.Device.capacity_ac.name,
    )

    inverter_dc_capacity_raw_kw = device_attribute_field(
        device_type=DeviceTypeEnum.PV_INVERTER,
        source_field_name=models.Device.capacity_dc.name,
    )

    # inverter module

    inverter_module_ac_capacity_raw_kw = device_attribute_field(
        device_type=DeviceTypeEnum.PV_INVERTER_MODULE,
        source_field_name=models.Device.capacity_ac.name,
    )
