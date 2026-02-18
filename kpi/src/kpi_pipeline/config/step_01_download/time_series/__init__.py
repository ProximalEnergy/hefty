from kpi_pipeline.config.step_01_download.time_series.bess import (
    DownloadTimeSeriesDataBESS,
)
from kpi_pipeline.config.step_01_download.time_series.pv import DownloadTimeSeriesPV


class DownloadTimeSeries(DownloadTimeSeriesDataBESS, DownloadTimeSeriesPV):
    pass
