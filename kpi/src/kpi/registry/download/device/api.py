from kpi.registry.download.device.bess.api import DownloadDeviceBess
from kpi.registry.download.device.pv.api import DownloadDevicePv


class DownloadDevice(DownloadDevicePv, DownloadDeviceBess):
    pass
