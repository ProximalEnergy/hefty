from typing import TYPE_CHECKING

from core.enumerations import DeviceType, SensorType
from kpi.base.protocol import (
    CalcProtocol,
    DeviceProtocol,
    HasInputsProtocol,
    ProjectAttributeProtocol,
    SensorProtocol,
)
from kpi.op.download.device.attribute import DeviceAttributeModel
from kpi.op.download.device.hierarchy import DeviceHierarchyModel
from kpi.op.download.project_attribute import Latitude, ProjectAttributeModel
from kpi.op.download.sensor import SensorModel
from kpi.op.field import NoInputs
from kpi.op.transform.unary import UnaryCalc

if TYPE_CHECKING:
    _no_inputs: HasInputsProtocol = NoInputs()

    _unary_calc: CalcProtocol = UnaryCalc(
        fn=lambda x: x,
        name="_",
    )

    _project_attr_model: ProjectAttributeProtocol = ProjectAttributeModel(
        source_field_name="latitude",
        scale=None,
        offset=None,
    )

    _project_attr_lat: ProjectAttributeProtocol = Latitude()

    _device_attribute: DeviceProtocol = DeviceAttributeModel(
        device_type=DeviceType.PROJECT,
        source_field_name="name_short",
        scale=None,
        offset=None,
    )

    _device_hierarchy: DeviceProtocol = DeviceHierarchyModel(
        child_device_type=DeviceType.PROJECT,
        parent_device_type=DeviceType.PROJECT,
    )

    _sensor_model: SensorProtocol = SensorModel(
        sensor_type=SensorType.METER_ACTIVE_POWER,
        project_level=False,
        scale=None,
        offset=None,
    )
