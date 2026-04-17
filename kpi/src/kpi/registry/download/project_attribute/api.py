from kpi.registry.download.project_attribute.bess import DownloadProjectAttributeBess
from kpi.registry.download.project_attribute.pv import DownloadProjectAttributePv


class DownloadProjectAttribute(
    DownloadProjectAttributePv, DownloadProjectAttributeBess
):
    pass
