from core.enumerations import DeviceType
from kpi.op.download.device.attribute import (
    device_attribute_field,
)
from kpi.op.download.device.schema import DeviceSchema

from core import models

field = device_attribute_field


class DownloadDevicePvAttribute(DeviceSchema):
    combiner_dc_capacity_raw_kw = field(
        device_type=DeviceType.PV_DC_COMBINER,
        source_field_name=models.Device.capacity_dc.name,
    )

    inverter_ac_capacity_raw_kw = field(
        device_type=DeviceType.PV_INVERTER,
        source_field_name=models.Device.capacity_ac.name,
    )

    inverter_dc_capacity_raw_kw = field(
        device_type=DeviceType.PV_INVERTER,
        source_field_name=models.Device.capacity_dc.name,
    )

    # inverter module

    inverter_module_ac_capacity_raw_kw = field(
        device_type=DeviceType.PV_INVERTER_MODULE,
        source_field_name=models.Device.capacity_ac.name,
    )
