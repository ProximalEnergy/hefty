from core.enumerations import DeviceTypeEnum

BASE_ENERGY_CAPACITY_ROLL_UP: dict[DeviceTypeEnum, DeviceTypeEnum | None] = {
    DeviceTypeEnum.BESS_STRING: DeviceTypeEnum.BESS_STRING,
    DeviceTypeEnum.BESS_ENCLOSURE: DeviceTypeEnum.BESS_STRING,
    DeviceTypeEnum.BESS_BANK: DeviceTypeEnum.BESS_STRING,
    DeviceTypeEnum.BESS_PCS_MODULE: DeviceTypeEnum.BESS_STRING,
    DeviceTypeEnum.BESS_PCS_MODULE_GROUP: DeviceTypeEnum.BESS_STRING,
    DeviceTypeEnum.BESS_DC_SKID: DeviceTypeEnum.BESS_STRING,
    DeviceTypeEnum.BESS_PCS: DeviceTypeEnum.BESS_STRING,
    DeviceTypeEnum.BESS_MVT: DeviceTypeEnum.BESS_STRING,
    DeviceTypeEnum.BESS_BLOCK: DeviceTypeEnum.BESS_STRING,
    DeviceTypeEnum.BESS_FEEDER: DeviceTypeEnum.BESS_STRING,
    DeviceTypeEnum.BESS_MV_COLLECTOR_CIRCUIT_METER: DeviceTypeEnum.BESS_STRING,
    DeviceTypeEnum.PPC: DeviceTypeEnum.BESS_STRING,
    DeviceTypeEnum.METER: DeviceTypeEnum.BESS_STRING,
    DeviceTypeEnum.PROJECT: DeviceTypeEnum.BESS_STRING,
}

BASE_POWER_CAPACITY_AC_ROLL_UP: dict[DeviceTypeEnum, DeviceTypeEnum | None] = {
    DeviceTypeEnum.BESS_PCS_MODULE: DeviceTypeEnum.BESS_PCS_MODULE,
    DeviceTypeEnum.BESS_PCS_MODULE_GROUP: DeviceTypeEnum.BESS_PCS_MODULE,
    DeviceTypeEnum.BESS_DC_SKID: DeviceTypeEnum.BESS_PCS_MODULE,
    DeviceTypeEnum.BESS_PCS: DeviceTypeEnum.BESS_PCS_MODULE,
    DeviceTypeEnum.BESS_MVT: DeviceTypeEnum.BESS_MVT,
    DeviceTypeEnum.BESS_BLOCK: DeviceTypeEnum.BESS_MVT,
    DeviceTypeEnum.BESS_FEEDER: DeviceTypeEnum.BESS_MVT,
    DeviceTypeEnum.BESS_MV_COLLECTOR_CIRCUIT_METER: DeviceTypeEnum.BESS_MVT,
    DeviceTypeEnum.PV_INVERTER_MODULE: DeviceTypeEnum.PV_INVERTER_MODULE,
    DeviceTypeEnum.PV_INVERTER: DeviceTypeEnum.PV_INVERTER,
    DeviceTypeEnum.PV_MVT: DeviceTypeEnum.PV_MVT,
    DeviceTypeEnum.PV_BLOCK: DeviceTypeEnum.PV_MVT,
    DeviceTypeEnum.PV_FEEDER: DeviceTypeEnum.PV_MVT,
    DeviceTypeEnum.PV_MV_COLLECTOR_CIRCUIT: DeviceTypeEnum.PV_MVT,
    DeviceTypeEnum.PV_MV_COLLECTOR_CIRCUIT_METER: DeviceTypeEnum.PV_MVT,
    DeviceTypeEnum.PPC: DeviceTypeEnum.PPC,
    DeviceTypeEnum.METER: DeviceTypeEnum.PPC,
    DeviceTypeEnum.PROJECT: DeviceTypeEnum.PPC,
}

BASE_POWER_CAPACITY_DC_ROLL_UP: dict[DeviceTypeEnum, DeviceTypeEnum | None] = {
    DeviceTypeEnum.DC_FIELD: DeviceTypeEnum.DC_FIELD,
    DeviceTypeEnum.PV_DC_COMBINER: DeviceTypeEnum.DC_FIELD,
    DeviceTypeEnum.PV_INVERTER_MODULE: DeviceTypeEnum.DC_FIELD,
    DeviceTypeEnum.PV_INVERTER: DeviceTypeEnum.DC_FIELD,
    DeviceTypeEnum.PV_MVT: DeviceTypeEnum.DC_FIELD,
    DeviceTypeEnum.PV_BLOCK: DeviceTypeEnum.DC_FIELD,
    DeviceTypeEnum.PV_FEEDER: DeviceTypeEnum.DC_FIELD,
    DeviceTypeEnum.PV_MV_COLLECTOR_CIRCUIT: DeviceTypeEnum.DC_FIELD,
    DeviceTypeEnum.PV_MV_COLLECTOR_CIRCUIT_METER: DeviceTypeEnum.DC_FIELD,
    DeviceTypeEnum.PPC: DeviceTypeEnum.DC_FIELD,
    DeviceTypeEnum.METER: DeviceTypeEnum.DC_FIELD,
    DeviceTypeEnum.PROJECT: DeviceTypeEnum.DC_FIELD,
}
