from kpi.workflow.download.device.bess.workflow import DownloadDeviceBess
from kpi.workflow.download.device.pv.workflow import DownloadDevicePv


class DownloadDevice(DownloadDevicePv, DownloadDeviceBess):
    pass
