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
    def extract_values(cls, *, enum_list: Sequence["BaseIntEnum"]) -> list[int]:
        """Extract integer values from a list of BaseEnum enums for database queries.

        Args:
            enum_list: Sequence of enum members to extract ids from.
        """
        return [status.value for status in enum_list]

    @classmethod
    def validate_against_database(cls, *, session: "Session") -> dict[str, Any]:
        """Compare enum members against rows in the configured lookup table.

        Args:
            session: SQLAlchemy session used to query the lookup table.
        """
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
        cls,
        *,
        session: "Session",
    ) -> dict[str, dict]:
        """
        Validate all enum subclasses against their database tables.

        Args:
            session: Database session to use for validation
            case_sensitive: Whether to perform case-sensitive name comparison
                (default: True)

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


class ProjectType(BaseIntEnum):
    _db_table = nonmember("operational.project_types")  # type: ignore[misc,assignment]
    _db_id_column = nonmember("project_type_id")  # type: ignore[misc,assignment]
    _db_name_column = nonmember("name_short")  # type: ignore[misc,assignment]

    PV = 1
    BESS = 2
    PVS = 3


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
    PV_INVERTER = 2
    PV_INVERTER_MODULE = 3
    MET_STATION = 4
    METER = 5
    PV_BLOCK = 6
    PPC = 7
    PV_DC_COMBINER = 9
    BESS_ENCLOSURE = 11
    BESS_BLOCK = 12
    BESS_PCS = 13
    PV_MVT = 15
    PV_MV_COLLECTOR_CIRCUIT = 16
    BESS_MV_CIRCUIT = 17
    PV_MV_COLLECTOR_CIRCUIT_METER = 19
    BESS_MV_CIRCUIT_METER = 20
    BESS_MV_AUX_METER = 21
    PV_FEEDER = 23
    BESS_FEEDER = 24
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
    BESS_DC_SKID = 36


class SensorType(BaseIntEnum):
    _db_table = nonmember("operational.sensor_types")  # type: ignore[misc,assignment]
    _db_id_column = nonmember("sensor_type_id")  # type: ignore[misc,assignment]
    _db_name_column = nonmember("name_short")  # type: ignore[misc,assignment]

    GHOST_UNKNOWN = 0
    METER_ACTIVE_POWER = 1
    PV_INVERTER_AC_POWER = 2
    PV_INVERTER_MODULE_AC_POWER = 3
    MET_STATION_POA = 4
    MET_STATION_GHI = 5
    MET_STATION_AMBIENT_TEMPERATURE = 6
    MET_STATION_WIND_SPEED = 7
    METER_REACTIVE_POWER = 8
    PV_INVERTER_AC_POWER_SETPOINT = 9
    METER_APPARENT_POWER = 10
    METER_FREQUENCY = 11
    METER_POWER_FACTOR = 12
    METER_DELIVERED_ENERGY = 13
    METER_CONSUMED_ENERGY = 14
    METER_NET_ENERGY = 15
    PV_BLOCK_AC_POWER = 16
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
    PV_BLOCK_ACTIVE_POWER_SETPOINT = 28
    BESS_BLOCK_SOC_PERCENT = 29
    BESS_BLOCK_SOC = 30
    BESS_PCS_AC_POWER = 31
    PROJECT_SOC_PERCENT = 32
    BESS_ENCLOSURE_TEMPERATURE = 33
    PV_INVERTER_MODULE_INTERNAL_TEMPERATURE = 34
    MET_STATION_GHI_TILT = 35
    MET_STATION_POA_TILT = 36
    MET_STATION_RELATIVE_HUMIDITY = 37
    PV_INVERTER_MODULE_DC_VOLTAGE = 38
    MET_STATION_SOIL_PERCENT = 39
    PV_MV_COLLECTOR_CIRCUIT_METER_ACTIVE_POWER = 40
    BESS_MV_CIRCUIT_METER_ACTIVE_POWER = 41
    BESS_ENCLOSURE_SOC_PERCENT = 43
    BESS_BANK_SOC_PERCENT = 44
    BESS_STRING_SOC_PERCENT = 45
    PV_INVERTER_STATUS = 46
    PV_INVERTER_MODULE_STATUS = 47
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
    PV_INVERTER_AC_NET_ENERGY = 69
    MET_STATION_BOM_TEMPERATURE = 70
    PV_INVERTER_MODULE_DC_CURRENT = 71
    PV_INVERTER_MODULE_DC_POWER = 72
    PV_INVERTER_MODULE_AC_ENERGY = 73
    PV_INVERTER_MODULE_POWER_FACTOR = 74
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
    PV_MVT_OIL_TEMPERATURE = 126
    BESS_STRING_MAX_CELL_VOLTAGE_POSITION = 127
    BESS_STRING_MIN_CELL_VOLTAGE_POSITION = 128
    BESS_STRING_MAX_MODULE_TEMPERATURE_POSITION = 129
    BESS_STRING_MIN_MODULE_TEMPERATURE_POSITION = 130
    BESS_STRING_SOC = 131
    PV_INVERTER_AC_APPARENT_POWER = 132
    PV_INVERTER_VOLTAGE_LL_AB = 133  # LL == Line to Line
    PV_INVERTER_VOLTAGE_LL_BC = 134  # LL == Line to Line
    PV_INVERTER_VOLTAGE_LL_CA = 135  # LL == Line to Line
    PV_INVERTER_REACTIVE_POWER = 136
    BESS_PCS_MODULE_STATUS = 137
    BESS_STRING_DISCHARGE_ENERGY_TOTAL = 138
    BESS_STRING_CHARGE_ENERGY_TOTAL = 139
    BESS_PCS_MODULE_ALARM = 140
    PV_INVERTER_REACTIVE_POWER_SETPOINT = 141
    BESS_PCS_STATUS = 142
    BESS_BANK_STATUS = 143
    PV_INVERTER_DC_VOLTAGE = 144
    BESS_STRING_STATUS = 145
    TRACKER_ROW_BATTERY_VOLTAGE = 146
    BESS_STRING_AVG_CELL_TEMPERATURE = 147
    BESS_STRING_MAX_CELL_TEMPERATURE = 148
    BESS_STRING_MIN_CELL_TEMPERATURE = 149
    BESS_PCS_AC_APPARENT_POWER = 151
    BESS_MV_CIRCUIT_METER_REACTIVE_POWER = 152
    BESS_MV_CIRCUIT_METER_POWER_FACTOR = 153
    BESS_MV_CIRCUIT_METER_DELIVERED_ENERGY = 154
    PV_MV_COLLECTOR_CIRCUIT_METER_CONSUMED_ENERGY = 155
    BESS_MV_CIRCUIT_METER_DELIVERED_REACTIVE_ENERGY = 156
    BESS_MV_CIRCUIT_METER_CONSUMED_REACTIVE_ENERGY = 157
    BESS_MV_AUX_METER_ACTIVE_POWER = 158
    BESS_MV_AUX_METER_REACTIVE_POWER = 159
    BESS_MV_AUX_METER_POWER_FACTOR = 160
    BESS_MV_AUX_METER_DELIVERED_ENERGY = 161
    BESS_MV_AUX_METER_CONSUMED_ENERGY = 162
    BESS_MV_AUX_METER_DELIVERED_REACTIVE_ENERGY = 163
    BESS_MV_AUX_METER_CONSUMED_REACTIVE_ENERGY = 164
    BESS_STRING_AVG_CELL_VOLTAGE_POSITION = 165
    BESS_STRING_MAX_CELL_TEMPERATURE_POSITION = 166
    BESS_STRING_MIN_CELL_TEMPERATURE_POSITION = 167
    BESS_STRING_POWER = 168
    PV_EXPECTED_POWER = 169
    BESS_PCS_MODULE_APPARENT_POWER = 170
    BESS_PCS_MODULE_CURRENT_PHASE_A = 171
    BESS_PCS_MODULE_CURRENT_PHASE_B = 172
    BESS_PCS_MODULE_CURRENT_PHASE_C = 173
    BESS_PCS_MODULE_VOLTAGE_LL_AB = 174
    BESS_PCS_MODULE_VOLTAGE_LL_BC = 175
    BESS_PCS_MODULE_VOLTAGE_LL_CA = 176
    BESS_STRING_SUM_CELL_VOLTAGE = 177
    BESS_PCS_MODULE_GROUP_CURRENT_PHASE_A = 178
    BESS_PCS_MODULE_GROUP_CURRENT_PHASE_B = 179
    BESS_PCS_MODULE_GROUP_CURRENT_PHASE_C = 180
    BESS_PCS_MODULE_GROUP_VOLTAGE_LL_AB = 181
    BESS_PCS_MODULE_GROUP_VOLTAGE_LL_BC = 182
    BESS_PCS_MODULE_GROUP_VOLTAGE_LL_CA = 183
    BESS_PCS_MODULE_GROUP_APPARENT_POWER = 184
    BESS_STRING_MAX_ALLOWABLE_CHARGE_CURRENT = 185
    BESS_STRING_MAX_ALLOWABLE_DISCHARGE_CURRENT = 186
    BESS_MODULE_ALARM = 187
    BESS_STRING_ALARM = 188
    PV_INVERTER_MODULE_REACTIVE_POWER = 189
    PV_INVERTER_MODULE_FREQUENCY = 190
    PV_INVERTER_MODULE_EFFICIENCY = 191
    PROJECT_LINE_TO_LINE_VOLTAGE = 192
    PV_INVERTER_MODULE_IGBT_TEMPERATURE = 193
    PV_INVERTER_MODULE_CURRENT_PHASE_A = 194
    PV_INVERTER_MODULE_CURRENT_PHASE_B = 195
    PV_INVERTER_MODULE_CURRENT_PHASE_C = 196
    PV_INVERTER_MODULE_VOLTAGE_PHASE_A = 197
    PV_INVERTER_MODULE_VOLTAGE_PHASE_B = 198
    PV_INVERTER_MODULE_VOLTAGE_PHASE_C = 199
    PV_INVERTER_DC_POWER = 200
    BESS_PCS_AVAILABLE_CAPACITIVE_REACTIVE_POWER = 201
    BESS_PCS_AVAILABLE_INDUCTIVE_REACTIVE_POWER = 202
    BESS_PCS_MODULE_AVAILABLE_INDUCTIVE_REACTIVE_POWER = 203
    BESS_PCS_MODULE_AVAILABLE_CAPACITIVE_REACTIVE_POWER = 204
    BESS_STRING_AVAILABLE_CHARGE_POWER = 205
    BESS_STRING_AVAILABLE_DISCHARGE_POWER = 206
    BESS_STRING_SOE_CHARGE_PERCENT = 207
    BESS_STRING_SOE_DISCHARGE_PERCENT = 208
    BESS_PCS_MODULE_GROUP_AVAILABLE_CAPACITIVE_REACTIVE_POWER = 209
    BESS_PCS_MODULE_GROUP_AVAILABLE_INDUCTIVE_REACTIVE_POWER = 210
    BESS_DC_SKID_SOC_PERCENT = 211
    METER_CURRENT = 212
    METER_CURRENT_PHASE_A = 213
    METER_CURRENT_PHASE_B = 214
    METER_CURRENT_PHASE_C = 215
    BESS_MV_CIRCUIT_METER_CONSUMED_ENERGY = 216


class KPIType(BaseIntEnum):
    _db_table = nonmember("operational.kpi_types")  # type: ignore[misc,assignment]
    _db_id_column = nonmember("kpi_type_id")  # type: ignore[misc,assignment]
    _db_name_column = nonmember("name_short")  # type: ignore[misc,assignment]

    PV_INVERTER_MECHANICAL_AVAILABILITY = 1
    PV_INVERTER_ENERGY_PRODUCTION = 2
    TRACKER_AVAILABILITY_BY_BLOCK = 3
    TRACKER_AVAILABILITY_BY_ROW = 4
    PROJECT_PV_INVERTER_MECHANICAL_AVAILABILITY = 5
    PROJECT_ENERGY_PRODUCTION = 6
    PV_INVERTER_MODULE_ENERGY_PRODUCTION = 7
    PV_DC_COMBINER_FIELD_HEALTH = 8
    PROJECT_CYCLE_COUNT = 9
    PROJECT_RESTING_SOC_PERCENT = 10
    BESS_BLOCK_CYCLE_COUNT = 11
    BESS_BLOCK_RESTING_SOC_PERCENT = 12
    BESS_BLOCK_AVERAGE_SOC_PERCENT = 15
    PROJECT_AVERAGE_SOC_PERCENT = 16
    MODULE_STATE_OF_HEALTH_BY_COMBINER = 17
    TRACKER_POSITION_DEVIATING_FROM_SETPOINT_BY_BLOCK = 18
    TRACKER_SETPOINT_DEVIATING_FROM_MEDIAN_BY_BLOCK = 19
    SUNGROW_BESS_TECHNICAL_AVAILABILITY_GUARANTEE = 20
    TRACKER_POSITION_DEVIATING_FROM_SETPOINT_BY_ROW = 21
    TRACKER_SETPOINT_DEVIATING_FROM_MEDIAN_BY_ROW = 22
    SMA_INVERTER_AVAILABILITY_UPTIME_PROJECT = 23
    BESS_BANK_AVERAGE_SOC_PERCENT = 24
    BESS_STRING_AVERAGE_SOC_PERCENT = 25
    BESS_DC_ENCLOSURE_AVERAGE_SOC_PERCENT = 26
    BESS_DC_ENCLOSURE_RESTING_SOC_PERCENT = 27
    BESS_DC_ENCLOSURE_CYCLE_COUNT = 28
    BESS_BANK_RESTING_SOC_PERCENT = 29
    BESS_STRING_RESTING_SOC_PERCENT = 30
    BESS_BANK_CYCLE_COUNT = 31
    BESS_STRING_CYCLE_COUNT = 32
    SPECIFIC_YIELD = 33
    PERFORMANCE_RATIO = 34
    BESS_PROJECT_ENERGY_CHARGED = 35
    BESS_BANK_ENERGY_CHARGED = 36
    BESS_STRING_ENERGY_CHARGED = 37
    BESS_MODULE_ENERGY_CHARGED = 38
    PROJECT_ENERGY_DISCHARGED = 39
    BESS_BANK_ENERGY_DISCHARGED = 40
    BESS_STRING_ENERGY_DISCHARGED = 41
    BESS_MODULE_ENERGY_DISCHARGED = 42
    PROJECT_RTE = 43
    BESS_BANK_RTE = 44
    BESS_STRING_RTE = 45
    BESS_MODULE_RTE = 46
    PROJECT_AVERAGE_DOD = 47
    BESS_BANK_DEPTH_OF_DISCHARGE = 48
    BESS_STRING_DEPTH_OF_DISCHARGE = 49
    BESS_MODULE_DEPTH_OF_DISCHARGE = 50
    C_RATE = 51
    PROJECT_SOH = 52
    BESS_BANK_SOH = 53
    BESS_STRING_SOH = 54
    BESS_MODULE_SOH = 55
    BESS_STRING_AVERAGE_C_RATE = 56
    BESS_BANK_AVAILABILITY = 57
    BESS_PCS_AVAILABILITY = 58
    BESS_STRING_MIN_MODULE_TEMP = 59
    BESS_STRING_MAX_MODULE_TEMP = 60
    BESS_STRING_AVG_MODULE_TEMP = 61
    BESS_STRING_AVG_C_RATE_WHILE_CHARGING = 62
    BESS_STRING_AVG_C_RATE_WHILE_DISCHARGING = 63
    BESS_STRING_MIN_CELL_VOLTAGE = 64
    BESS_STRING_AVG_CELL_VOLTAGE = 65
    BESS_STRING_MAX_CELL_VOLTAGE = 66
    BESS_STRING_AVG_CURRENT = 67
    BESS_STRING_MAX_CURRENT = 68
    BESS_STRING_MIN_CURRENT = 69
    BESS_STRING_AVG_CURRENT_WHILE_CHARGING = 70
    BESS_STRING_AVG_CURRENT_WHILE_DISCHARGING = 71
    BESS_STRING_AVG_CELL_TEMPERATURE = 72
    BESS_STRING_MAX_CELL_TEMPERATURE = 73
    BESS_STRING_MIN_CELL_TEMPERATURE = 74
    BESS_PROJECT_AVERAGE_C_RATE_WHILE_CHARGING = 75
    BESS_PROJECT_AVERAGE_C_RATE_WHILE_DISCHARGING = 76
    BESS_PCS_AVERAGE_C_RATE = 77
    BESS_PCS_AVERAGE_C_RATE_WHILE_CHARGING = 78
    BESS_PCS_AVERAGE_C_RATE_WHILE_DISCHARGING = 79
    BESS_STRING_DEGRADATION = 80
    BESS_PCS_HOURS_CHARGING = 81
    BESS_PCS_HOURS_DISCHARGING = 82
    BESS_PROJECT_HOURS_CHARGING = 83
    BESS_PROJECT_HOURS_DISCHARGING = 84
    BESS_PCS_HOURS_IDLING = 85
    BESS_PROJECT_HOURS_IDLING = 86
    BESS_PCS_ENERGY_CHARGED_DC = 87
    BESS_PCS_ENERGY_DISCHARGED_DC = 88
    BESS_PCS_AVG_REAL_AC_POWER_WHILE_CHARGING = 89
    BESS_PCS_AVG_REAL_AC_POWER_WHILE_DISCHARGING = 90
    BESS_PCS_EFFICIENCY_CHARGING = 91
    BESS_PCS_EFFICIENCY_DISCHARGING = 92
    BESS_MV_AUX_METER_ENERGY = 93
    BESS_PROJECT_CHARGE_CYCLES = 94
    BESS_PROJECT_DISCHARGE_CYCLES = 95
    BESS_STRING_AVAILABILITY = 96
    PV_PROJECT_SOLV_CONTRACTUAL_AVAILABILITY = 97
    PV_PROJECT_SOLV_PERIOD_MWH_PRODUCED = 98
    PV_PROJECT_SOLV_PERIOD_MWH_LOST = 99
    PV_PROJECT_PERFORMANCE_INDEX = 100
    PV_DC_COMBINER_MECHANICAL_AVAILABILITY = 101
    PV_PROJECT_EXPECTED_ENERGY_DELIVERED = 102
    PV_PROJECT_CURTAILMENT = 103
    BESS_PROJECT_MINIMUM_USABLE_ENERGY_CAPACITY = 104
    BESS_PROJECT_DC_ENCLOSURE_RTE = 105
    PROJECT_MAXIMUM_CONTINUOUS_DISCHARGED_ENERGY = 106
    BESS_PCS_MODULE_AVAILABILITY = 107
    BESS_STRING_MAXIMUM_CONTINUOUS_DISCHARGED_ENERGY = 108
    BESS_PCS_MAXIMUM_CONTINUOUS_DISCHARGED_ENERGY = 109
    BESS_PCS_MODULE_MAXIMUM_CONTINUOUS_DISCHARGED_ENERGY = 110
    BESS_CIRCUIT_ENERGY_CHARGED = 111
    BESS_CIRCUIT_ENERGY_DISCHARGED = 112
    BESS_PCS_MODULE_ENERGY_CHARGED = 113
    BESS_PCS_MODULE_ENERGY_DISCHARGED = 114
    BESS_PROJECT_ENERGY_CHARGED_NO_AUX = 115
    BESS_PROJECT_METER_TO_PCS_MODULE_CHARGE_EFFICIENCY = 116
    BESS_PROJECT_PCS_MODULE_TO_METER_DISCHARGE_EFFICIENCY = 117


class EventLossType(BaseIntEnum):
    _db_table = nonmember("operational.event_loss_types")  # type: ignore[misc,assignment]
    _db_id_column = nonmember("event_loss_type_id")  # type: ignore[misc,assignment]
    _db_name_column = nonmember("name_short")  # type: ignore[misc,assignment]

    PROXIMAL_ENERGY = 1
    PROXIMAL_FINANCIAL = 2
    PROXIMAL_PV_DC_CAPACITY = 3


class ReportType(BaseIntEnum):
    _db_table = nonmember("operational.report_types")  # type: ignore[misc,assignment]
    _db_id_column = nonmember("report_type_id")  # type: ignore[misc,assignment]
    _db_name_column = nonmember("name_short")  # type: ignore[misc,assignment]

    PERFORMANCE_SUMMARY = 1
    DC_AMPERAGE = 2
    MODULE_DEGRADATION = 3
    TRACKER_AVAILABILITY_POSITION_VS_SETPOINT = 4
    TRACKER_AVAILABILITY_POSITION_VS_MEDIAN_SETPOINT = 5
    INVERTER_MECHANICAL_AVAILABILITY = 6
    PPC_V_Q_CURVE_DIAGNOSTIC = 7
    PV_INVERTER_APPARENT_POWER_VS_AC_VOLTAGE = 8
    PV_PERFORMANCE_DAILY = 9
    EEC_BESS_MONTHLY_REPORT = 10
    SCADA_TELEMETRY_LAST_REPORTED = 11
    WIND_STOW = 12


# --- Other Enums ---


class DefaultKPITimeRange(IntEnum):
    ONE_MONTH = 1
    YEAR_TO_DATE = 2
    BEGINNING_OF_LIFE = 3
    MONTH_TO_DATE = 4


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


class AggregationMethod(StrEnum):
    FIRST = "first"
    AVERAGE = "avg"


class TimeOffset(StrEnum):
    NONE = "0min"
    ONE_MINUTE = "1min"
    FIVE_MINUTES = "5min"
    TEN_MINUTES = "10min"
    FIFTEEN_MINUTES = "15min"
    THIRTY_MINUTES = "30min"
    ONE_HOUR = "1hour"
    TWO_HOURS = "2hour"
    FOUR_HOURS = "4hour"
    SIX_HOURS = "6hour"
    EIGHT_HOURS = "8hour"
    TWELVE_HOURS = "12hour"
    TWENTY_FOUR_HOURS = "24hour"


class TimeInterval(StrEnum):
    ONE_MINUTE = "1min"
    FIVE_MINUTES = "5min"
    TEN_MINUTES = "10min"
    FIFTEEN_MINUTES = "15min"
    THIRTY_MINUTES = "30min"
    ONE_HOUR = "1hour"


class ProjectDataInterval(StrEnum):
    MQTT = "mqtt"
    ONE_SEC = "1sec"
    ONE_MINUTE = "1min"
    FIVE_MINUTES = "5min"


class PVBudgetedSoilingMode(StrEnum):
    FIXED = "fixed"
    PER_TIMESTAMP = "per_timestamp"


class ReactionType(StrEnum):
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    FIRE = "fire"
    EYES = "eyes"
    QUESTION_MARK = "question_mark"
    HEART = "heart"
    LAUGHING = "laughing"
    SURPRISED = "surprised"
    SAD = "sad"
    ANGRY = "angry"
    PARTY = "party"
    CHECK = "check"
    CLAP = "clap"
    HUNDRED = "hundred"
    ROCKET = "rocket"
    LIGHTBULB = "lightbulb"
    STAR = "star"
    TARGET = "target"
    PRAY = "pray"


class NotificationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class NotificationType(BaseIntEnum):
    _db_table = nonmember("admin.notification_types")  # type: ignore[misc,assignment]
    _db_id_column = nonmember("notification_type_id")  # type: ignore[misc,assignment]
    _db_name_column = nonmember("name_short")  # type: ignore[misc,assignment]

    HAIL = 1
    FIRE = 2
    TORNADO = 3
    WIND = 4
    CALENDAR_REMINDER = 5
    EVENT_CHAT_MESSAGE = 6
    KPI_THRESHOLD = 7


class NotificationChannel(StrEnum):
    EMAIL = "email"
    IN_APP = "in_app"


class NotificationState(StrEnum):
    UNREAD = "unread"
    READ = "read"
    DELETED = "deleted"


class ClaimSubmissionChannel(StrEnum):
    EMAIL = "email"
    PORTAL = "portal"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


class ClaimStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ClaimUpdateType(StrEnum):
    STATUS_CHANGE = "status_change"
    SUBMISSION = "submission"
    OEM_MESSAGE = "oem_message"
    NOTE = "note"
    PARTS = "parts"
    FIELD_VISIT = "field_visit"


class ProjectDatabaseProvider(StrEnum):
    TIMESCALE = "timescale"
    CLICKHOUSE = "clickhouse"


class OutputType(StrEnum):
    """Enum to select DbQuery fetch output type."""

    PANDAS = "pandas"
    POLARS = "polars"
    SQLALCHEMY = "sqlalchemy"


class PGDataType(IntEnum):
    UNKNOWN = 0
    INTEGER = 1
    BIGINT = 2
    REAL = 3
    DOUBLE = 4
    BOOLEAN = 5
    TEXT = 6
