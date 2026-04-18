from kpi.registry.download.device.bess.attribute import DownloadDeviceBessAttribute
from kpi.registry.download.device.bess.hierarchy import DownloadDeviceBessHierarchy
from kpi.registry.download.device.pv.attribute import DownloadDevicePvAttribute
from kpi.registry.download.device.pv.hierarchy import DownloadDevicePvHierarchy


class DownloadDevice(
    DownloadDevicePvHierarchy,
    DownloadDevicePvAttribute,
    DownloadDeviceBessHierarchy,
    DownloadDeviceBessAttribute,
):
    pass
