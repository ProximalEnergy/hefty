from kpi.workflow.download.device_attribute.bess import (
    DownloadDeviceAttributeBess,
)
from kpi.workflow.download.device_attribute.pv import DownloadDeviceAttributePv


class DownloadDeviceAttribute(DownloadDeviceAttributePv, DownloadDeviceAttributeBess):
    pass
