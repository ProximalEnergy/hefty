from enum import StrEnum

from core.enumerations import DeviceType

UTC = "UTC"


class Time(StrEnum):
    TIME_5MIN_UTC = "time_5min_utc"
    DATE_LOCAL = "date_local"


is_utc_map: dict[Time, bool] = {
    Time.TIME_5MIN_UTC: True,
    Time.DATE_LOCAL: False,
}

freq_map: dict[Time, str] = {
    Time.TIME_5MIN_UTC: "5min",
    Time.DATE_LOCAL: "D",
}


class Aggregation(StrEnum):
    MEAN = "mean"
    MAX = "max"
    MIN = "min"
    SUM = "sum"


supported_devices: list[DeviceType] = [
    DeviceType.BESS_PCS,
    DeviceType.BESS_BLOCK,
    DeviceType.BESS_PCS_MODULE,
    DeviceType.BESS_STRING,
    DeviceType.PV_BLOCK,
    DeviceType.PV_DC_COMBINER,
    DeviceType.PV_PCS,
    DeviceType.MET_STATION,
    DeviceType.TRACKER_ROW,
    DeviceType.PV_INVERTER_MODULE,
    DeviceType.BESS_BLOCK,
    DeviceType.BESS_ENCLOSURE,
]


class DataType(StrEnum):
    FLOAT = "float64"
    INT = "int"
    BOOL = "bool"
