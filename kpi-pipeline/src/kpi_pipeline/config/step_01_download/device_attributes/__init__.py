from kpi_pipeline.config.step_01_download.device_attributes.bess import (
    DownloadDevAttrsBESS,
)
from kpi_pipeline.config.step_01_download.device_attributes.pv import (
    DownloadDeviceAttrsPV,
)


class DownloadDeviceAttrs(DownloadDevAttrsBESS, DownloadDeviceAttrsPV):
    pass
