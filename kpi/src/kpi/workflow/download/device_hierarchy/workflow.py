from kpi.workflow.download.device_hierarchy.bess import (
    DownloadDeviceHierarchyBess,
)
from kpi.workflow.download.device_hierarchy.pv import DownloadDeviceHierarchyPv


class DownloadDeviceHierarchy(DownloadDeviceHierarchyPv, DownloadDeviceHierarchyBess):
    pass
