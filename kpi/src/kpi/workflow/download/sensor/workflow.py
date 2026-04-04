from kpi.workflow.download.sensor.bess import DownloadSensorBess
from kpi.workflow.download.sensor.pv import DownloadSensorPv


class DownloadSensor(DownloadSensorPv, DownloadSensorBess):
    pass
