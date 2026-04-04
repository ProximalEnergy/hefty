from enum import StrEnum


class Attrs(StrEnum):
    PROJECT_NAME_SHORT = "project_name_short"
    START_DATE = "start_date"
    END_DATE = "end_date"
    TIME_ZONE = "time_zone"


class TimeCoords(StrEnum):
    TIME_5MIN_UTC = "time_5min_utc"
    DATE_LOCAL = "date_local"


class ProjectNameShort(StrEnum):
    BEXAR = "bexar"
