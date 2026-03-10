from kpi_pipeline.config.step_01_download.device_attributes import DownloadDeviceAttrs
from kpi_pipeline.config.step_01_download.events import DownloadEvents
from kpi_pipeline.config.step_01_download.expected_energy import DownloadExpectedEnergy
from kpi_pipeline.config.step_01_download.project_attributes import DownloadProjAttrs
from kpi_pipeline.config.step_01_download.statuses import DownloadStatus
from kpi_pipeline.config.step_01_download.time_series import DownloadTimeSeries
from kpi_pipeline.services.schema import SchemaMergeSchema


class Download(SchemaMergeSchema):
    project_attributes = DownloadProjAttrs
    device_attributes = DownloadDeviceAttrs
    time_series = DownloadTimeSeries
    status = DownloadStatus
    expected_energy = DownloadExpectedEnergy
    events = DownloadEvents
