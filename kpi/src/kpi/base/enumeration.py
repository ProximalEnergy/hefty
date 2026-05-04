from enum import StrEnum

from pydantic import BaseModel


class TimeCoord(StrEnum):
    TIME_5MIN_UTC = "time_5min_utc"
    TIME_15MIN_UTC = "time_15min_utc"
    HOUR_UTC = "hour_utc"
    DATE_LOCAL = "date_local"


NEW_NAME = "new_name"


class TimeDescriptor(BaseModel):
    pandas_freq: str
    utc: bool = True


TIME_DESCRIPTOR: dict[TimeCoord, TimeDescriptor] = {
    TimeCoord.TIME_5MIN_UTC: TimeDescriptor(pandas_freq="5min"),
    TimeCoord.TIME_15MIN_UTC: TimeDescriptor(pandas_freq="15min"),
    TimeCoord.HOUR_UTC: TimeDescriptor(pandas_freq="h"),
    TimeCoord.DATE_LOCAL: TimeDescriptor(pandas_freq="D", utc=False),
}
