from kpi.workflow.download.project_attribute.bess import DownloadProjectAttributeBess
from kpi.workflow.download.project_attribute.pv import DownloadProjectAttributePv


class DownloadProjectAttribute(
    DownloadProjectAttributePv, DownloadProjectAttributeBess
):
    pass
