from kpi.op.download.device.schema import DeviceSchema
from kpi.op.download.event import EventSchema
from kpi.op.download.expected_energy import ExpectedEnergySchema
from kpi.op.download.project_attribute import ProjectAttributeSchema
from kpi.op.download.sensor import SensorSchema
from kpi.op.download.status import StatusSchema
from kpi.op.pipeline_schema import PipelineSchema, Schema
from kpi.registry.download.device.api import DownloadDevice
from kpi.registry.download.event import DownloadEvent
from kpi.registry.download.expected_energy import DownloadExpectedEnergy
from kpi.registry.download.project_attribute.api import DownloadProjectAttribute
from kpi.registry.download.sensor.api import DownloadSensor
from kpi.registry.download.status import DownloadStatus


class DownloadSchema(PipelineSchema):
    download_event = Schema(EventSchema(map=DownloadEvent.map()))
    download_expected_energy = Schema(
        ExpectedEnergySchema(map=DownloadExpectedEnergy.map())
    )
    download_device = Schema(DeviceSchema(map=DownloadDevice.map()))
    download_project_attribute = Schema(
        ProjectAttributeSchema(map=DownloadProjectAttribute.map())
    )
    download_sensor = Schema(SensorSchema(map=DownloadSensor.map()))
    download_status = Schema(StatusSchema(map=DownloadStatus.map()))
