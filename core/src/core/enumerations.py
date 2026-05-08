from collections.abc import Sequence
from enum import Enum, IntEnum, StrEnum, nonmember
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from sqlalchemy import text


class BaseDatabaseEnum[DatabaseEnumValueT]:
    _db_table: str | None = None
    _db_id_column: str | None = None
    _db_name_column: str | None = None

    @classmethod
    def _database_id_type(cls) -> type[Any] | None:
        if not issubclass(cls, Enum):
            return None

        enum_cls = cast(type[Enum], cls)
        members = list(enum_cls)
        if not members:
            return None

        return type(members[0].value)

    @classmethod
    def _coerce_database_id(cls, *, value: Any) -> DatabaseEnumValueT:
        if cls._database_id_type() is UUID:
            return cast(DatabaseEnumValueT, UUID(str(value)))

        return cast(DatabaseEnumValueT, value)

    @classmethod
    def _db_order_column(cls) -> str | None:
        if cls._database_id_type() is UUID:
            return cls._db_name_column

        return cls._db_id_column

    @classmethod
    def _enum_subclasses(cls) -> list[type["BaseDatabaseEnum[Any]"]]:
        enum_subclasses: list[type[BaseDatabaseEnum[Any]]] = []
        for subclass in cls.__subclasses__():
            if not issubclass(subclass, BaseDatabaseEnum):
                continue
            if issubclass(subclass, Enum):
                enum_subclasses.append(subclass)
            enum_subclasses.extend(subclass._enum_subclasses())

        return enum_subclasses

    @classmethod
    def extract_values(
        cls,
        *,
        enum_list: Sequence["BaseDatabaseEnum[DatabaseEnumValueT]"],
    ) -> list[DatabaseEnumValueT]:
        """Extract enum values from a list of enums for database queries.

        Args:
            enum_list: Sequence of enum members to extract ids from.
        """
        return [
            cls._coerce_database_id(value=cast(Enum, member).value)
            for member in enum_list
        ]

    @classmethod
    def validate_against_database(cls, *, session: "Session") -> dict[str, Any]:
        """Compare enum members against rows in the configured lookup table.

        Args:
            session: SQLAlchemy session used to query the lookup table.
        """
        table = cls._db_table
        id_column = cls._db_id_column
        name_column = cls._db_name_column
        order_column = cls._db_order_column()
        enum_cls = cast(type[Enum], cls)
        enum_data = {
            cls._coerce_database_id(value=member.value): member.name
            for member in enum_cls
        }

        if (
            table is None
            or id_column is None
            or name_column is None
            or order_column is None
        ):
            return {
                "missing_in_db": "Un-monitored",
                "extra_in_db": "None",
                "name_mismatches": "None",
                "valid": "None",
                "total_enum_count": 0,
                "total_db_count": 0,
            }

        if not table or not id_column or not name_column or not order_column:
            raise ValueError("Database table and column names must be defined")

        # SQL injection risk, but this library is not exposed to anybody
        # outside of Proximal
        query = text(
            f"SELECT {id_column}, {name_column} "  # noqa: S608
            f"FROM {table} ORDER BY {order_column}"
        )

        result = session.execute(query).fetchall()
        db_data = {cls._coerce_database_id(value=row[0]): row[1] for row in result}

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
            names_match = enum_name.lower() == str(db_name).lower()
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

        Returns:
            Dictionary mapping enum class names to their validation results
        """
        results: dict[str, dict[str, Any]] = {}

        for subclass in cls._enum_subclasses():
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
class ProjectStatusType(BaseDatabaseEnum[int], IntEnum):
    _db_table = nonmember(  # type: ignore[misc]
        "operational.project_status_types"
    )
    _db_id_column = nonmember("project_status_type_id")  # type: ignore[misc]
    _db_name_column = nonmember("name_short")  # type: ignore[misc]

    ACTIVE = 1
    ONBOARDING = 2
    ARCHIVED = 3


class ProjectTypeEnum(BaseDatabaseEnum[int], IntEnum):
    _db_table = nonmember("operational.project_types")  # type: ignore[misc]
    _db_id_column = nonmember("project_type_id")  # type: ignore[misc]
    _db_name_column = nonmember("name_short")  # type: ignore[misc]

    PV = 1
    BESS = 2
    PVS = 3
    WIND = 4
    SIMPLE_CYCLE_GT = 5


class ProjectID(BaseDatabaseEnum[UUID], Enum):
    _db_table = nonmember("operational.projects")  # type: ignore[misc]
    _db_id_column = nonmember("project_id")  # type: ignore[misc]
    _db_name_column = nonmember("name_short")  # type: ignore[misc]

    ASSEMBLY_1 = UUID("b102379c-eadb-4cc4-808b-a3d4b3f3ea5a")
    ASSEMBLY_2 = UUID("32fac373-1dd6-465a-bb06-d3cc6b268c7b")
    ASSEMBLY_3 = UUID("23bd9f17-07b0-4a15-be56-bc676f9b7463")
    BEXAR = UUID("3b63ea38-cf28-4880-810e-41a81209d640")
    CARRIZO_SPRINGS = UUID("2824c119-35fb-48a3-82e9-854c8e331c5e")
    CENTENNIAL_FLATS = UUID("bee3f2dc-995e-4f2c-b409-ff66f51c97eb")
    CONTINENTAL = UUID("75c901ca-fa81-49cb-ab2b-de50c1c0eb65")
    CONTINENTAL_V2 = UUID("5662003f-4d3a-4ed1-ba7c-781981a0f0b1")
    CRANE = UUID("c4eb9ee4-e943-450e-914a-a92ae60994f9")
    DOUBLE_BLACK_DIAMOND = UUID("6970fba7-6462-475f-805a-2357ee4ababb")
    EL_CENTRO = UUID("d7047189-8548-4bd9-a44d-e9021a054e7b")
    ESCONDIDO = UUID("36c23224-9b26-4bb0-9569-87d98d0eb217")
    EXCELSIOR_DOCUMENTS = UUID("37f66167-d10a-4262-9651-bc416f574961")
    FALFURRIAS = UUID("1e86f87d-da60-40b9-b21e-6a6700801c32")
    FALFURRIAS_INDIE = UUID("8560c515-3b29-426a-88ed-05abb1a7d13b")
    FIDDLERS_CANYON_1 = UUID("7988693d-5fbe-491f-90ed-fb48b9e1d099")
    FIDDLERS_CANYON_2 = UUID("5e5c8458-1c17-4b2c-907b-fb9bed045884")
    FIDDLERS_CANYON_3 = UUID("3a8c68a6-7176-48f9-a27c-aa9669d443bc")
    GEARS_HARRIS = UUID("ba9e5acc-e8be-4c8b-b976-3100a921e6c6")
    GOODWIN = UUID("7da47737-5587-4beb-b614-d9b434b95a80")
    GREGORY = UUID("623ddc81-ed4c-4e56-b9ca-a4a9be238a8b")
    GREGORY_INDIE = UUID("c947895b-e067-4e21-9972-6c2aed17b52a")
    HEADCAMP = UUID("56a117c4-e045-45f1-aa52-e2e862d18cb0")
    HEARN_ROAD = UUID("9d74f427-1f30-4090-b3bc-03cae8be0bd4")
    HIDDEN_VALLEY = UUID("4a457efc-99aa-4961-a5b0-d25f477adf01")
    LANCASTER = UUID("3028d2ee-c924-4c6e-a133-9938926bc4b6")
    LAURELES = UUID("69c1e2b9-87e7-44a5-9ee1-a69650084090")
    LEAKY = UUID("68bb58e2-e9b2-4081-aa56-e60dc33d9ecd")
    LYSSY = UUID("f4852649-0284-4463-b2e2-f7a756e36741")
    MASON = UUID("85e02759-1033-4e1d-a1a6-ad86f5200aaf")
    MASON_INDIE = UUID("0da615ac-5364-49bc-a577-dda3866e34cb")
    MEADOW_PARK = UUID("69a3055f-2422-4eee-902f-5eaca158491d")
    MEDINA = UUID("86ab9305-76ac-4434-b1d3-2c54f5c33287")
    MEDINA_LAKE = UUID("16a37540-e21f-4619-8724-ad02be05ffd2")
    MILFORD_2 = UUID("f4ba3efd-01b7-45aa-8c74-9f07447e9d85")
    MILTON = UUID("200fb929-04d2-4bc2-ad84-774837db517a")
    MONTE_CRISTO = UUID("38d93404-f79f-4ea9-8c08-f2d2c4f370b6")
    MONTE_CRISTO_INDIE = UUID("f4427a0c-2d70-436c-ab28-facb1c4b4d1f")
    MUENSTER = UUID("1c1c945f-97af-4eb3-afe6-0acbb3409b82")
    MUENSTER_INDIE = UUID("f90c2f87-1700-41c8-858e-fcf793ae1e4e")
    MUSTANG_HILLS = UUID("fbb656c2-9ede-40b3-9bdd-89d2e1dcd643")
    MUSTANG_HILLS_BESS = UUID("b7eb64c0-dceb-4c58-89c6-0b02808e6ad1")
    NORTH_STAR = UUID("e69ddc19-e2c6-4537-a236-93849c4bc847")
    PALACIOS = UUID("cba2690a-03cf-4878-bf0b-dd3801da6fb2")
    PALACIOS_INDIE = UUID("ea902794-4670-4a95-b2bd-cf700a6ca460")
    PINTAIL = UUID("2378f9bb-6f3c-489a-87a0-8ec25fc29d95")
    POWERHOUSE_PLANT = UUID("949897b9-7709-40fb-84d9-52b24419793e")
    PRAIRIE_BREEZE_II = UUID("dbb493ba-acf5-427d-9648-47f9ac666a0e")
    PRAIRIE_BREEZE_III = UUID("8ee19feb-1b2d-4dc3-aa05-eb0d0d8d3a97")
    PROJECT_DEFAULT = UUID("e8434ff5-b6da-46fc-b057-f9f84b13b61b")
    ROSAMOND_SOUTH_1 = UUID("838e5fe1-7d20-47e2-a438-d34e8e081a19")
    SERRANO = UUID("043fecf7-6cce-4228-acda-b1f23fd6d5f5")
    SIGURD = UUID("83e51c6e-22ff-4ea2-8b3b-5bf89185409d")
    SINTON_PIRATE = UUID("fe1f0db0-c492-49a0-8502-ffc6eee22e55")
    SINTON_PIRATE_INDIE = UUID("e34b7e5b-b2f8-4b50-9127-953144021889")
    SKYHAWK = UUID("cd617920-de65-48cd-a3ff-66272ba55b5e")
    SNIPESVILLE_2 = UUID("679f8f19-af11-43e0-9a60-64fc706f92a4")
    SOUTH_MILFORD = UUID("f1f18240-41f5-4c3c-8602-77526dbbbd1f")
    SUN_POND = UUID("3f9d3a72-8322-4d5a-8f37-1eac89f9ee59")
    SUN_STREAMS_3 = UUID("fa8c717a-9a9f-4759-ada9-de845fa9b59f")
    SUN_STREAMS_4 = UUID("3e3a98c1-3172-407e-b730-827f389c294d")
    TILDEN = UUID("2d9cb07b-bb1c-4e05-bc52-2bbd416ebf0b")
    UTOPIA = UUID("755836fa-c3ec-4ec9-8362-648709df30f7")
    WHITE_CREEK = UUID("b36cb3c2-2d78-4d14-b89d-126bd5d0455e")


class UserTypeEnum(BaseDatabaseEnum[int], IntEnum):
    _db_table = nonmember("admin.user_types")  # type: ignore[misc]
    _db_id_column = nonmember("user_type_id")  # type: ignore[misc]
    _db_name_column = nonmember("name_short")  # type: ignore[misc]

    SUPERADMIN = 1
    ADMIN = 2
    USER = 3


class DeviceTypeEnum(BaseDatabaseEnum[int], IntEnum):
    _db_table = nonmember("operational.device_types")  # type: ignore[misc]
    _db_id_column = nonmember("device_type_id")  # type: ignore[misc]
    _db_name_column = nonmember("name_short")  # type: ignore[misc]

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
    BESS_MV_COLLECTOR_CIRCUIT = 17
    PV_MV_COLLECTOR_CIRCUIT_METER = 19
    BESS_MV_COLLECTOR_CIRCUIT_METER = 20
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


class SensorTypeEnum(BaseDatabaseEnum[int], IntEnum):
    _db_table = nonmember("operational.sensor_types")  # type: ignore[misc]
    _db_id_column = nonmember("sensor_type_id")  # type: ignore[misc]
    _db_name_column = nonmember("name_short")  # type: ignore[misc]

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
    METER_ENERGY_EXPORTED_TO_GRID = 13
    METER_ENERGY_IMPORTED_TO_PROJECT = 14
    METER_NET_ENERGY = 15
    PV_BLOCK_AC_POWER = 16
    PPC_ACTIVE_POWER = 17
    PPC_REACTIVE_POWER = 18
    PPC_APPARENT_POWER = 19
    PPC_POWER_FACTOR = 20
    PPC_ACTIVE_POWER_SETPOINT = 21
    PPC_REACTIVE_POWER_SETPOINT = 22
    PPC_POWER_FACTOR_SETPOINT = 23
    TRACKER_ROW_POSITION = 24
    TRACKER_ROW_SETPOINT = 25
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
    BESS_MV_COLLECTOR_CIRCUIT_METER_ACTIVE_POWER = 41
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
    METER_REACTIVE_ENERGY_EXPORTED_TO_GRID = 75
    METER_REACTIVE_ENERGY_IMPORTED_TO_PROJECT = 76
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
    BESS_MV_COLLECTOR_CIRCUIT_METER_REACTIVE_POWER = 152
    BESS_MV_COLLECTOR_CIRCUIT_METER_POWER_FACTOR = 153
    BESS_MV_COLLECTOR_CIRCUIT_METER_ENERGY_EXPORTED_TO_GRID = 154
    PV_MV_COLLECTOR_CIRCUIT_METER_ENERGY_IMPORTED_TO_PROJECT = 155
    BESS_MV_COLLECTOR_CIRCUIT_METER_REACTIVE_ENERGY_EXPORTED_TO_GRID = 156
    BESS_MV_COLLECTOR_CIRCUIT_METER_REACTIVE_ENERGY_IMPORTED_TO_PROJECT = 157
    BESS_MV_AUX_METER_ACTIVE_POWER = 158
    BESS_MV_AUX_METER_REACTIVE_POWER = 159
    BESS_MV_AUX_METER_POWER_FACTOR = 160
    BESS_MV_AUX_METER_ENERGY_EXPORTED_TO_GRID = 161
    BESS_MV_AUX_METER_ENERGY_IMPORTED_TO_PROJECT = 162
    BESS_MV_AUX_METER_REACTIVE_ENERGY_EXPORTED_TO_GRID = 163
    BESS_MV_AUX_METER_REACTIVE_ENERGY_IMPORTED_TO_PROJECT = 164
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
    BESS_MV_COLLECTOR_CIRCUIT_METER_ENERGY_IMPORTED_TO_PROJECT = 216
    MET_STATION_WIND_DIRECTION = 217
    PROJECT_BREAKER_STATUS = 218
    PROJECT_RECLOSER_STATUS = 219
    TRACKER_ZONE_WIND_SPEED = 220


class ExpectedMetricIdEnum(BaseDatabaseEnum[int], IntEnum):
    """Expected metric IDs used by EEM expected power outputs."""

    PV_DC_COMBINER_POWER_DEGRADATION = 1
    PV_DC_COMBINER_POWER_SOILING_DEGRADATION = 2
    PV_PCS_POWER_DEGRADATION = 3
    PV_PCS_POWER_SOILING_DEGRADATION = 4
    PV_POI_POWER_DEGRADATION = 5
    PV_POI_POWER_SOILING_DEGRADATION = 6
    PV_DC_COMBINER_POWER_BASE = 7
    PV_DC_COMBINER_POWER_SOILING = 8
    PV_PCS_POWER_BASE = 9
    PV_PCS_POWER_SOILING = 10
    PV_POI_POWER_BASE = 11
    PV_POI_POWER_SOILING = 12
    PV_DC_COMBINER_POAI_BASE = 13


class KPITypeEnum(BaseDatabaseEnum[int], IntEnum):
    _db_table = nonmember("operational.kpi_types")  # type: ignore[misc]
    _db_id_column = nonmember("kpi_type_id")  # type: ignore[misc]
    _db_name_column = nonmember("name_short")  # type: ignore[misc]

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
    BESS_PROJECT_STRING_SOC_VARIANCE = 118
    BESS_PCS_STRING_SOC_VARIANCE = 119
    BESS_PROJECT_STRING_SOC_BALANCE_SCORE = 120
    BESS_PCS_STRING_SOC_BALANCE_SCORE = 121
    PV_PROJECT_INVERTER_MODULE_TO_METER_EFFICIENCY = 122
    BESS_PROJECT_POWER_AVAILABILITY = 123
    BESS_PROJECT_ENERGY_AVAILABILITY = 124
    BESS_PROJECT_NER_AVAILABILITY = 125
    BESS_PROJECT_SYSTEM_AVAILABILITY = 126


class EventLossTypeEnum(BaseDatabaseEnum[int], IntEnum):
    _db_table = nonmember(  # type: ignore[misc]
        "operational.event_loss_types"
    )
    _db_id_column = nonmember("event_loss_type_id")  # type: ignore[misc]
    _db_name_column = nonmember("name_short")  # type: ignore[misc]

    PROXIMAL_ENERGY = 1
    PROXIMAL_FINANCIAL = 2
    PROXIMAL_PV_DC_CAPACITY = 3


class ReportTypeEnum(BaseDatabaseEnum[int], IntEnum):
    _db_table = nonmember("operational.report_types")  # type: ignore[misc]
    _db_id_column = nonmember("report_type_id")  # type: ignore[misc]
    _db_name_column = nonmember("name_short")  # type: ignore[misc]

    PERFORMANCE_SUMMARY = 1
    DC_AMPERAGE = 2
    MODULE_DEGRADATION = 3
    TRACKER_ROW_AVAILABILITY_POSITION_VS_SETPOINT = 4
    TRACKER_ROW_AVAILABILITY_POSITION_VS_MEDIAN_SETPOINT = 5
    INVERTER_MECHANICAL_AVAILABILITY = 6
    PPC_V_Q_CURVE_DIAGNOSTIC = 7
    PV_INVERTER_APPARENT_POWER_VS_AC_VOLTAGE = 8
    PV_PERFORMANCE_DAILY = 9
    EEC_BESS_MONTHLY_REPORT = 10
    SCADA_TELEMETRY_LAST_REPORTED = 11
    WIND_STOW = 12
    MONTHLY_PERFORMANCE = 13
    PV_PERFORMANCE_WEEKLY = 14


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


class ReactionTypeEnum(StrEnum):
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


class NotificationTypeEnum(BaseDatabaseEnum[int], IntEnum):
    _db_table = nonmember("admin.notification_types")  # type: ignore[misc]
    _db_id_column = nonmember("notification_type_id")  # type: ignore[misc]
    _db_name_column = nonmember("name_short")  # type: ignore[misc]

    HAIL = 1
    FIRE = 2
    TORNADO = 3
    WIND = 4
    CALENDAR_REMINDER = 5
    EVENT_CHAT_MESSAGE = 6
    KPI_THRESHOLD = 7
    DATA_CONNECTION_OUTAGE = 8
    PROJECT_CAPACITY_REDUCTION = 9


class NotificationChannelEnum(StrEnum):
    EMAIL = "email"
    IN_APP = "in_app"


class NotificationStateEnum(StrEnum):
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


class PGDataTypeEnum(IntEnum):
    UNKNOWN = 0
    INTEGER = 1
    BIGINT = 2
    REAL = 3
    DOUBLE = 4
    BOOLEAN = 5
    TEXT = 6
