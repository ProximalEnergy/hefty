from typing import TYPE_CHECKING

from kpi.base.protocol import SchemaClassProtocol, SchemaProtocol
from kpi.op.download.device.schema import DeviceSchema
from kpi.op.download.event import EventSchema
from kpi.op.download.expected_energy import ExpectedEnergySchema
from kpi.op.download.project_attribute import ProjectAttributeSchema
from kpi.op.download.sensor import SensorSchema
from kpi.op.download.status import StatusSchema
from kpi.op.schema_registry import SchemaRegistry
from kpi.op.transform.schema import CalcSchema
from kpi.op.upload import UploadSchema

if TYPE_CHECKING:
    _device_class: SchemaClassProtocol = DeviceSchema
    _device_schema: SchemaProtocol = DeviceSchema()

    _event_class: SchemaClassProtocol = EventSchema
    _event_schema: SchemaProtocol = EventSchema()

    _expected_energy_class: SchemaClassProtocol = ExpectedEnergySchema
    _expected_energy_schema: SchemaProtocol = ExpectedEnergySchema()

    _project_attribute_class: SchemaClassProtocol = ProjectAttributeSchema
    _project_attribute_schema: SchemaProtocol = ProjectAttributeSchema()

    _status_class: SchemaClassProtocol = StatusSchema
    _status_schema: SchemaProtocol = StatusSchema()

    _sensor_class: SchemaClassProtocol = SensorSchema
    _sensor_schema: SchemaProtocol = SensorSchema()

    _calc_class: SchemaClassProtocol = CalcSchema
    _calc_schema: SchemaProtocol = CalcSchema()

    _schema_class: SchemaClassProtocol = SchemaRegistry
    _schema_registry: SchemaProtocol = SchemaRegistry()

    _upload_class: SchemaClassProtocol = UploadSchema
    _upload_schema: SchemaProtocol = UploadSchema()
