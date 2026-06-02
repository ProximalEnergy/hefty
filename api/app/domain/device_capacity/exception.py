from app.domain.device_capacity.base_capacity_roll_up import (
    BASE_POWER_CAPACITY_AC_ROLL_UP,
)
from core.enumerations import DeviceTypeEnum as D
from core.enumerations import ProjectID

ENERGY_CAPACITY_ROLL_UP_PER_PROJECT: dict[ProjectID, dict[D, D | None]] = {
    ProjectID.SERRANO: {
        D.BESS_MV_COLLECTOR_CIRCUIT: D.BESS_MV_COLLECTOR_CIRCUIT,
        D.BESS_MV_COLLECTOR_CIRCUIT_METER: D.BESS_MV_COLLECTOR_CIRCUIT,
        D.PPC: D.BESS_MV_COLLECTOR_CIRCUIT,
        D.METER: D.BESS_MV_COLLECTOR_CIRCUIT,
        D.PROJECT: D.BESS_MV_COLLECTOR_CIRCUIT,
    },
    ProjectID.SUN_STREAMS_4: {
        D.BESS_MV_COLLECTOR_CIRCUIT_METER: D.BESS_MV_COLLECTOR_CIRCUIT_METER,
        D.PPC: D.BESS_MV_COLLECTOR_CIRCUIT_METER,
        D.METER: D.BESS_MV_COLLECTOR_CIRCUIT_METER,
        D.PROJECT: D.BESS_MV_COLLECTOR_CIRCUIT_METER,
    },
    ProjectID.SUN_POND: {
        D.PPC: D.PPC,
        D.METER: D.PPC,
        D.PROJECT: D.PPC,
    },
}

POWER_AC_CAPACITY_ROLL_UP_PER_PROJECT: dict[ProjectID, dict[D, D | None]] = {
    ProjectID.SERRANO: BASE_POWER_CAPACITY_AC_ROLL_UP
    | {
        D.BESS_MV_COLLECTOR_CIRCUIT: D.BESS_MV_COLLECTOR_CIRCUIT,
        D.BESS_MV_COLLECTOR_CIRCUIT_METER: D.BESS_MV_COLLECTOR_CIRCUIT,
    },
    ProjectID.SUN_STREAMS_3: BASE_POWER_CAPACITY_AC_ROLL_UP
    | {
        D.BESS_PCS: D.BESS_PCS,
    },
    ProjectID.SUN_STREAMS_4: BASE_POWER_CAPACITY_AC_ROLL_UP
    | {
        D.BESS_MV_COLLECTOR_CIRCUIT_METER: D.BESS_MV_COLLECTOR_CIRCUIT_METER,
    },
}

pv_dc_combiner_roll_up: dict[D, D | None] = {
    D.PV_DC_COMBINER: D.PV_DC_COMBINER,
    D.PV_INVERTER_MODULE: D.PV_DC_COMBINER,
    D.PV_INVERTER: D.PV_DC_COMBINER,
    D.PV_MVT: D.PV_DC_COMBINER,
    D.PV_BLOCK: D.PV_DC_COMBINER,
    D.PV_FEEDER: D.PV_DC_COMBINER,
    D.PV_MV_COLLECTOR_CIRCUIT: D.PV_DC_COMBINER,
    D.PV_MV_COLLECTOR_CIRCUIT_METER: D.PV_DC_COMBINER,
    D.PPC: D.PV_DC_COMBINER,
    D.METER: D.PV_DC_COMBINER,
    D.PROJECT: D.PV_DC_COMBINER,
}

POWER_DC_CAPACITY_ROLL_UP_PER_PROJECT: dict[ProjectID, dict[D, D | None]] = {
    ProjectID.DOUBLE_BLACK_DIAMOND: pv_dc_combiner_roll_up,
    ProjectID.SUN_STREAMS_3: pv_dc_combiner_roll_up,
    ProjectID.FIDDLERS_CANYON_1: pv_dc_combiner_roll_up,
    ProjectID.FIDDLERS_CANYON_2: pv_dc_combiner_roll_up,
    ProjectID.FIDDLERS_CANYON_3: pv_dc_combiner_roll_up,
    ProjectID.MILFORD_2: pv_dc_combiner_roll_up,
    ProjectID.SOUTH_MILFORD: pv_dc_combiner_roll_up,
    ProjectID.SUN_STREAMS_4: pv_dc_combiner_roll_up,
}
