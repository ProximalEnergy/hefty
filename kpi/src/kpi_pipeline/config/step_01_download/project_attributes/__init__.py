from kpi_pipeline.config.step_01_download.project_attributes.bess import (
    DownloadProjAttrsBESS,
)
from kpi_pipeline.config.step_01_download.project_attributes.general import (
    DownloadProjAttrsGeneral,
)
from kpi_pipeline.config.step_01_download.project_attributes.pv import (
    DownloadProjAttrsPV,
)


class DownloadProjAttrs(
    DownloadProjAttrsGeneral, DownloadProjAttrsBESS, DownloadProjAttrsPV
):
    pass
