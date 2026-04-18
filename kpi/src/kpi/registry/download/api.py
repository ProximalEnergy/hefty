from kpi.registry.download.device.api import DownloadDevice
from kpi.registry.download.event import DownloadEvent
from kpi.registry.download.expected_energy import DownloadExpectedEnergy
from kpi.registry.download.project_attribute.api import DownloadProjectAttribute
from kpi.registry.download.sensor.api import DownloadSensor
from kpi.registry.download.status import DownloadStatus


class Download(
    DownloadStatus,
    DownloadSensor,
    DownloadProjectAttribute,
    DownloadExpectedEnergy,
    DownloadEvent,
    DownloadDevice,
):
    pass
