from kpi.registry.download.sensor.bess import DownloadSensorBess
from kpi.registry.download.sensor.pv import DownloadSensorPv


class DownloadSensor(DownloadSensorPv, DownloadSensorBess):
    pass
