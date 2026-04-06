from kpi.service.schema_registry import Schema, SchemaRegistry
from kpi.workflow.download.device.workflow import DownloadDevice
from kpi.workflow.download.event import DownloadEventBess
from kpi.workflow.download.expected_energy import DownloadExpectedEnergy
from kpi.workflow.download.project_attribute.workflow import DownloadProjectAttribute
from kpi.workflow.download.sensor.workflow import DownloadSensor
from kpi.workflow.download.status import DownloadStatusBess


class Download(SchemaRegistry):
    device = Schema(DownloadDevice)
    event = Schema(DownloadEventBess)
    expected_energy = Schema(DownloadExpectedEnergy)
    project_attribute = Schema(DownloadProjectAttribute)
    sensor = Schema(DownloadSensor)
    status = Schema(DownloadStatusBess)
