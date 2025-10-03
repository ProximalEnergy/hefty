from collections.abc import Sequence
from enum import IntEnum, StrEnum, nonmember
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from sqlalchemy import text


class BaseIntEnum(IntEnum):
    _db_table = nonmember(None)
    _db_id_column = nonmember(None)
    _db_name_column = nonmember(None)

    @classmethod
    def extract_values(  # skip-star-syntax
        cls, enum_list: Sequence["BaseIntEnum"]
    ) -> list[int]:
        """Extract integer values from a list of BaseEnum enums for database queries."""
        return [status.value for status in enum_list]

    @classmethod
    def validate_against_database(cls, *, session: "Session") -> dict[str, Any]:
        table = cls._db_table
        id_column = cls._db_id_column
        name_column = cls._db_name_column
        enum_data = {member.value: member.name for member in cls}

        if table is None or id_column is None or name_column is None:
            return {
                "missing_in_db": "Un-monitored",
                "extra_in_db": "None",
                "name_mismatches": "None",
                "valid": "None",
                "total_enum_count": 0,
                "total_db_count": 0,
            }

        if not table or not id_column or not name_column:
            raise ValueError("Database table and column names must be defined")

        # SQL injection risk, but this library is not exposed to anybody
        # outside of Proximal
        query = text(
            f"SELECT {id_column}, {name_column} FROM {table} ORDER BY {id_column}"  # noqa: S608
        )

        result = session.execute(query).fetchall()
        db_data = {row[0]: row[1] for row in result}

        # Find discrepancies
        enum_ids = set(enum_data.keys())
        db_ids = set(db_data.keys())

        missing_in_db = []
        for enum_id in enum_ids - db_ids:
            missing_in_db.append({"id": enum_id, "enum_name": enum_data[enum_id]})

        extra_in_db = []
        for db_id in db_ids - enum_ids:
            extra_in_db.append({"id": db_id, "db_name": db_data[db_id]})

        name_mismatches = []
        for common_id in enum_ids & db_ids:
            enum_name = enum_data[common_id]
            db_name = db_data[common_id]
            names_match = enum_name.lower() == db_name.lower()
            if not names_match:
                name_mismatches.append(
                    {"id": common_id, "enum_name": enum_name, "db_name": db_name}
                )

        is_valid = not missing_in_db and not extra_in_db and not name_mismatches

        return {
            "missing_in_db": missing_in_db,
            "extra_in_db": extra_in_db,
            "name_mismatches": name_mismatches,
            "valid": is_valid,
            "total_enum_count": len(enum_data),
            "total_db_count": len(db_data),
        }

    @classmethod
    def validate_all_enums(
        cls, *, session: "Session", case_sensitive: bool = True
    ) -> dict[str, dict]:
        """
        Validate all enum subclasses against their database tables.

        Args:
            session: Database session to use for validation
            case_sensitive: Whether to perform case-sensitive name comparison (default: True)

        Returns:
            Dictionary mapping enum class names to their validation results
        """
        results: dict[str, dict[str, Any]] = {}

        # Find all BaseIntEnum subclasses
        for subclass in cls.__subclasses__():
            if (
                subclass._db_table
                and subclass._db_id_column
                and subclass._db_name_column
            ):
                results[subclass.__name__] = subclass.validate_against_database(
                    session=session
                )

        return results


# --- Database Enums ---
class ProjectStatusType(BaseIntEnum):
    _db_table = nonmember("operational.project_status_types")  # type: ignore[misc,assignment]
    _db_id_column = nonmember("project_status_type_id")  # type: ignore[misc,assignment]
    _db_name_column = nonmember("name_short")  # type: ignore[misc,assignment]

    ACTIVE = 1
    ONBOARDING = 2
    ARCHIVED = 3


class UserTypeEnum(BaseIntEnum):
    _db_table = nonmember("admin.user_types")  # type: ignore[misc,assignment]
    _db_id_column = nonmember("user_type_id")  # type: ignore[misc,assignment]
    _db_name_column = nonmember("name_short")  # type: ignore[misc,assignment]

    SUPERADMIN = 1
    ADMIN = 2
    USER = 3


class DeviceType(BaseIntEnum):
    _db_table = nonmember("operational.device_types")  # type: ignore[misc,assignment]
    _db_id_column = nonmember("device_type_id")  # type: ignore[misc,assignment]
    _db_name_column = nonmember("name_short")  # type: ignore[misc,assignment]

    GHOST = 0
    PROJECT = 1
    PV_PCS = 2
    PV_PCS_MODULE = 3
    MET_STATION = 4
    METER = 5
    BLOCK = 6
    PPC = 7
    TRACKER = 8
    PV_DC_COMBINER = 9
    TRACKER_PV_PCS = 10
    BESS_ENCLOSURE = 11
    BESS_BLOCK = 12
    BESS_PCS = 13
    CIRCUIT = 14
    MVT = 15
    PV_MV_CIRCUIT = 16
    BESS_MV_CIRCUIT = 17
    STATION_METER = 18
    PV_MV_CIRCUIT_METER = 19
    BESS_MV_CIRCUIT_METER = 20
    BESS_MV_AUX_METER = 21
    BACKUP_METER = 22
    PV_CIRCUIT = 23
    BESS_CIRCUIT = 24
    BESS_MVT = 25
    BESS_BANK = 26
    BESS_STRING = 27
    TRACKER_ZONE = 28
    TRACKER_ROW = 29
    DC_FIELD = 30
    BESS_CELL = 31
    BESS_PCS_MODULE_GROUP = 32
    BESS_PCS_MODULE = 33
    BESS_MODULE = 34
    PV_MODULE = 35


class SensorType(BaseIntEnum):
    _db_table = nonmember("operational.sensor_types")  # type: ignore[misc,assignment]
    _db_id_column = nonmember("sensor_type_id")  # type: ignore[misc,assignment]
    _db_name_column = nonmember("name_short")  # type: ignore[misc,assignment]

    GHOST_UNKNOWN = 0
    METER_ACTIVE_POWER = 1
    PV_PCS_AC_POWER = 2
    PV_PCS_MODULE_AC_POWER = 3
    MET_STATION_POA = 4
    MET_STATION_GHI = 5
    MET_STATION_AMBIENT_TEMPERATURE = 6
    MET_STATION_WIND_SPEED = 7
    METER_REACTIVE_POWER = 8
    PV_PCS_AC_POWER_SETPOINT = 9
    METER_APPARENT_POWER = 10
    METER_FREQUENCY = 11
    METER_POWER_FACTOR = 12
    METER_DELIVERED_ENERGY = 13
    METER_CONSUMED_ENERGY = 14
    METER_NET_ENERGY = 15
    BLOCK_AC_POWER = 16
    PPC_ACTIVE_POWER = 17
    PPC_REACTIVE_POWER = 18
    PPC_APPARENT_POWER = 19
    PPC_POWER_FACTOR = 20
    PPC_ACTIVE_POWER_SETPOINT = 21
    PPC_REACTIVE_POWER_SETPOINT = 22
    PPC_POWER_FACTOR_SETPOINT = 23
    TRACKER_POSITION = 24
    TRACKER_SETPOINT = 25
    TRACKER_STOW_COMMAND = 26
    PV_DC_COMBINER_CURRENT = 27
    BLOCK_ACTIVE_POWER_SETPOINT = 28
    BESS_BLOCK_SOC_PERCENT = 29
    BESS_BLOCK_SOC = 30
    BESS_PCS_AC_POWER = 31
    PROJECT_SOC_PERCENT = 32
    BESS_ENCLOSURE_TEMPERATURE = 33
    PV_PCS_MODULE_INTERNAL_TEMPERATURE = 34
    MET_STATION_GHI_TILT = 35
    MET_STATION_POA_TILT = 36
    MET_STATION_RELATIVE_HUMIDITY = 37
    PV_PCS_MODULE_DC_VOLTAGE = 38
    MET_STATION_SOIL_PERCENT = 39
    PV_MV_CIRCUIT_METER_ACTIVE_POWER = 40
    BESS_MV_CIRCUIT_METER_ACTIVE_POWER = 41
    BESS_ENCLOSURE_SOC_PERCENT = 43
    BESS_BANK_SOC_PERCENT = 44
    BESS_STRING_SOC_PERCENT = 45
    PV_PCS_STATUS = 46
    PV_PCS_MODULE_STATUS = 47
    TRACKER_ZONE_STATUS = 48
    TRACKER_ROW_STATUS = 49
    BESS_BANK_CURRENT = 50
    BESS_BANK_VOLTAGE = 51
    BESS_BANK_MAX_CELL_TEMPERATURE = 52
    BESS_BANK_MIN_CELL_TEMPERATURE = 53
    BESS_BANK_MAX_CELL_VOLTAGE = 54
    BESS_BANK_MIN_CELL_VOLTAGE = 55
    BESS_BANK_SOH_PERCENT = 56
    BESS_STRING_CURRENT = 57
    BESS_STRING_VOLTAGE = 58
    BESS_STRING_SOH_PERCENT = 59
    BESS_STRING_MAX_CELL_VOLTAGE = 60
    BESS_STRING_MIN_CELL_VOLTAGE = 61
    BESS_STRING_AVG_CELL_VOLTAGE = 62
    BESS_STRING_MAX_MODULE_TEMPERATURE = 63
    BESS_STRING_MIN_MODULE_TEMPERATURE = 64
    BESS_STRING_AVG_MODULE_TEMPERATURE = 65
    BESS_PCS_FREQUENCY = 66
    BESS_PCS_POWER_FACTOR = 67
    BESS_PCS_REACTIVE_POWER = 68
    PV_PCS_AC_NET_ENERGY = 69
    MET_STATION_BOM_TEMPERATURE = 70
    PV_PCS_MODULE_DC_CURRENT = 71
    PV_PCS_MODULE_DC_POWER = 72
    PV_PCS_MODULE_AC_ENERGY = 73
    PV_PCS_MODULE_POWER_FACTOR = 74
    METER_DELIVERED_REACTIVE_ENERGY = 75
    METER_CONSUMED_REACTIVE_ENERGY = 76
    TRACKER_ZONE_POSITION = 77
    TRACKER_ZONE_SETPOINT = 78
    BESS_ENCLOSURE_SOC = 79
    BESS_PCS_AVAILABLE_CHARGE_POWER = 80
    BESS_PCS_AVAILABLE_DISCHARGE_POWER = 81
    BESS_CELL_VOLTAGE = 82
    BESS_PCS_DC_CURRENT = 83
    BESS_PCS_DC_POWER = 84
    BESS_PCS_DC_VOLTAGE = 85
    BESS_PCS_CHARGE_ENERGY_DAILY = 86
    BESS_PCS_CHARGE_ENERGY_MONTHLY = 87
    BESS_PCS_CHARGE_ENERGY_YEARLY = 88
    BESS_PCS_CHARGE_ENERGY_TOTAL = 89
    BESS_PCS_DISCHARGE_ENERGY_DAILY = 90
    BESS_PCS_DISCHARGE_ENERGY_MONTHLY = 91
    BESS_PCS_DISCHARGE_ENERGY_YEARLY = 92
    BESS_PCS_DISCHARGE_ENERGY_TOTAL = 93
    PPC_VOLTAGE = 94
    PPC_VOLTAGE_SETPOINT = 95
    BESS_PCS_MODULE_FREQUENCY = 96
    BESS_PCS_MODULE_DC_CURRENT = 97
    BESS_PCS_MODULE_POWER_FACTOR = 98
    BESS_PCS_MODULE_AVAILABLE_CHARGE_POWER = 99
    BESS_PCS_MODULE_AVAILABLE_DISCHARGE_POWER = 100
    BESS_PCS_MODULE_CHARGE_ENERGY_DAILY = 101
    BESS_PCS_MODULE_CHARGE_ENERGY_TOTAL = 102
    BESS_PCS_MODULE_DC_POWER = 103
    BESS_PCS_MODULE_DISCHARGE_ENERGY_DAILY = 104
    BESS_PCS_MODULE_DISCHARGE_ENERGY_TOTAL = 105
    BESS_PCS_MODULE_AC_POWER = 106
    BESS_PCS_MODULE_REACTIVE_POWER = 107
    BESS_PCS_MODULE_CABINET_TEMPERATURE = 108
    BESS_PCS_MODULE_IGBT_TEMPERATURE = 109
    BESS_PCS_MODULE_DC_VOLTAGE = 110
    BESS_PCS_MODULE_GROUP_FREQUENCY = 111
    BESS_PCS_MODULE_GROUP_DC_CURRENT = 112
    BESS_PCS_MODULE_GROUP_POWER_FACTOR = 113
    BESS_PCS_MODULE_GROUP_AVAILABLE_CHARGE_POWER = 114
    BESS_PCS_MODULE_GROUP_AVAILABLE_DISCHARGE_POWER = 115
    BESS_PCS_MODULE_GROUP_CHARGE_ENERGY_DAILY = 116
    BESS_PCS_MODULE_GROUP_CHARGE_ENERGY_TOTAL = 117
    BESS_PCS_MODULE_GROUP_DC_POWER = 118
    BESS_PCS_MODULE_GROUP_DISCHARGE_ENERGY_DAILY = 119
    BESS_PCS_MODULE_GROUP_DISCHARGE_ENERGY_TOTAL = 120
    BESS_PCS_MODULE_GROUP_AC_POWER = 121
    BESS_PCS_MODULE_GROUP_REACTIVE_POWER = 122
    BESS_PCS_MODULE_GROUP_CABINET_TEMPERATURE = 123
    BESS_PCS_MODULE_GROUP_IGBT_TEMPERATURE = 124
    BESS_PCS_MODULE_GROUP_DC_VOLTAGE = 125
    MVT_OIL_TEMPERATURE = 126
    BESS_STRING_MAX_CELL_VOLTAGE_POSITION = 127
    BESS_STRING_MIN_CELL_VOLTAGE_POSITION = 128
    BESS_STRING_MAX_MODULE_TEMPERATURE_POSITION = 129
    BESS_STRING_MIN_MODULE_TEMPERATURE_POSITION = 130
    BESS_STRING_SOC = 131
    PV_PCS_AC_APPARENT_POWER = 132
    PV_PCS_AC_LINE_VOLTAGE_AB = 133
    PV_PCS_AC_LINE_VOLTAGE_BC = 134
    PV_PCS_AC_LINE_VOLTAGE_CA = 135
    PV_PCS_REACTIVE_POWER = 136
    BESS_PCS_MODULE_STATUS = 137
    BESS_STRING_DISCHARGE_ENERGY_TOTAL = 138
    BESS_STRING_CHARGE_ENERGY_TOTAL = 139
    BESS_PCS_MODULE_ALARM = 140
    PV_PCS_REACTIVE_POWER_SETPOINT = 141
    BESS_PCS_STATUS = 142
    BESS_BANK_STATUS = 143
    PV_PCS_DC_VOLTAGE = 144
    BESS_STRING_STATUS = 145
    TRACKER_ROW_BATTERY_VOLTAGE = 146
    BESS_STRING_AVG_CELL_TEMPERATURE = 147
    BESS_STRING_MAX_CELL_TEMPERATURE = 148
    BESS_STRING_MIN_CELL_TEMPERATURE = 149
    BESS_PCS_AC_APPARENT_POWER = 151


# --- Other Enums ---


class DefaultKPITimeRange(IntEnum):
    ONE_MONTH = 1
    YEAR_TO_DATE = 2
    BEGINNING_OF_LIFE = 3


class RackingArchitecture(IntEnum):
    PORTRAIT = 1
    LANDSCAPE = 2


class DefaultTimeRange(IntEnum):
    PAST_TWO_DAYS = 1
    PAST_THREE_DAYS = 2
    TODAY = 3
    YESTERDAY = 4


class ComponentType(IntEnum):
    BAR = 1
    GAUGE = 2
    LINE = 3
    SCATTER = 4
    KPI = 5
    GIS = 6
    RICH_TEXT = 7
    TEXT = 8


class AggregationType(StrEnum):
    LAST = "last"
    AVERAGE = "avg"


class PVBudgetedSoilingMode(StrEnum):
    FIXED = "fixed"
    PER_TIMESTAMP = "per_timestamp"
