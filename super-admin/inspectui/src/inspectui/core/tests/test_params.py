"""Git-tracked shared test defaults using core enumerations."""

from typing import Any

from core.enumerations import DeviceTypeEnum, SensorTypeEnum

TEST_PARAMS: dict[str, dict[str, Any]] = {
    "sensor_type_unique_per_device": {
        "sensor_type_ids": [
            SensorTypeEnum.BESS_STRING_DISCHARGE_ENERGY_TOTAL,
            SensorTypeEnum.BESS_STRING_CHARGE_ENERGY_TOTAL,
        ],
    },
    "parent_device_type_allowlist": {
        "child_parent_type_rules": {
            # ===== PV =====
            DeviceTypeEnum.DC_FIELD: [DeviceTypeEnum.PV_DC_COMBINER],
            DeviceTypeEnum.PV_DC_COMBINER: [
                DeviceTypeEnum.PV_INVERTER_MODULE,
                DeviceTypeEnum.PV_INVERTER,
            ],
            DeviceTypeEnum.PV_INVERTER_MODULE: [DeviceTypeEnum.PV_INVERTER],
            DeviceTypeEnum.PV_INVERTER: [DeviceTypeEnum.PV_MVT],
            DeviceTypeEnum.PV_MVT: [DeviceTypeEnum.PV_BLOCK],
            DeviceTypeEnum.TRACKER_ROW: [DeviceTypeEnum.TRACKER_ZONE],
            DeviceTypeEnum.TRACKER_ZONE: [DeviceTypeEnum.PV_BLOCK],
            DeviceTypeEnum.MET_STATION: [DeviceTypeEnum.PV_BLOCK],
            DeviceTypeEnum.PV_BLOCK: [
                # If there is MV/HV equipment, Blocks will map to Feeders
                DeviceTypeEnum.PV_FEEDER,
                # No Feeders: Blocks map to MV Collector Circuits
                DeviceTypeEnum.PV_MV_COLLECTOR_CIRCUIT,
                # If there is not MV/HV equipment, Blocks will map to the PPC
                DeviceTypeEnum.PPC,
            ],
            DeviceTypeEnum.PV_FEEDER: [
                # If there are MV Collector Circuits, Feeders will map to Circuits
                DeviceTypeEnum.PV_MV_COLLECTOR_CIRCUIT,
                # If there are not MV Collector Circuits, Feeders will map to the PPC
                DeviceTypeEnum.PPC,
            ],
            DeviceTypeEnum.PV_MV_COLLECTOR_CIRCUIT: [
                # If there are MV Collector Circuit Meters, Circuits will map to Meters
                DeviceTypeEnum.PV_MV_COLLECTOR_CIRCUIT_METER,
                # No MV Collector Circuit Meters: Circuits map to PPC
                DeviceTypeEnum.PPC,
            ],
            DeviceTypeEnum.PV_MV_COLLECTOR_CIRCUIT_METER: [DeviceTypeEnum.PPC],
            # ===== BESS =====
            DeviceTypeEnum.BESS_CELL: [DeviceTypeEnum.BESS_MODULE],
            DeviceTypeEnum.BESS_MODULE: [DeviceTypeEnum.BESS_STRING],
            DeviceTypeEnum.BESS_STRING: [DeviceTypeEnum.BESS_ENCLOSURE],
            DeviceTypeEnum.BESS_ENCLOSURE: [
                # If there are Banks, Enclosures will map to Banks
                DeviceTypeEnum.BESS_BANK,
                # If there are not Banks, Enclosures will map to PCS Module Groups
                DeviceTypeEnum.BESS_PCS_MODULE_GROUP,
                # If there are not PCS Module Groups, Enclosures will map to PCS Modules
                DeviceTypeEnum.BESS_PCS_MODULE,
                # If there are not PCS Modules, Enclosures will map to PCSs
                DeviceTypeEnum.BESS_PCS,
            ],
            DeviceTypeEnum.BESS_BANK: [
                # If there are PCS Module Groups, Banks will map to Module Groups
                DeviceTypeEnum.BESS_PCS_MODULE_GROUP,
                # If there are not Module Groups, Banks will map to PCS Modules
                DeviceTypeEnum.BESS_PCS_MODULE,
            ],
            DeviceTypeEnum.BESS_PCS_MODULE: [
                # If there are PCS Module Groups, PCS Modules will map to Module Groups
                DeviceTypeEnum.BESS_PCS_MODULE_GROUP,
                # No PCS Module Groups: PCS Modules map to BESS DC Skid
                DeviceTypeEnum.BESS_DC_SKID,
            ],
            DeviceTypeEnum.BESS_PCS_MODULE_GROUP: [DeviceTypeEnum.BESS_DC_SKID],
            DeviceTypeEnum.BESS_DC_SKID: [DeviceTypeEnum.BESS_PCS],
            DeviceTypeEnum.BESS_PCS: [DeviceTypeEnum.BESS_MVT],
            DeviceTypeEnum.BESS_MVT: [DeviceTypeEnum.BESS_BLOCK],
            DeviceTypeEnum.BESS_BLOCK: [
                # If there is MV/HV equipment, Blocks will map to Feeders
                DeviceTypeEnum.BESS_FEEDER,
                # No Feeders: Blocks map to MV Collector Circuits
                DeviceTypeEnum.BESS_MV_COLLECTOR_CIRCUIT,
                # If there is not MV/HV equipment, Blocks will map to the PPC
                DeviceTypeEnum.PPC,
            ],
            DeviceTypeEnum.BESS_FEEDER: [DeviceTypeEnum.BESS_MV_COLLECTOR_CIRCUIT],
            DeviceTypeEnum.BESS_MV_COLLECTOR_CIRCUIT: [
                DeviceTypeEnum.BESS_MV_COLLECTOR_CIRCUIT_METER
            ],
            DeviceTypeEnum.BESS_MV_COLLECTOR_CIRCUIT_METER: [DeviceTypeEnum.PPC],
            # ===== SYSTEM =====
            DeviceTypeEnum.PPC: [DeviceTypeEnum.METER],
            DeviceTypeEnum.METER: [DeviceTypeEnum.PROJECT],
        },
    },
    "required_device_models": {
        "device_type_ids": [
            DeviceTypeEnum.PV_INVERTER,
            DeviceTypeEnum.BESS_CELL,
            DeviceTypeEnum.BESS_MODULE,
            DeviceTypeEnum.BESS_STRING,
            DeviceTypeEnum.BESS_DC_SKID,
            DeviceTypeEnum.BESS_PCS,
        ],
    },
    "required_device_types": {
        "pv_device_type_ids": [
            DeviceTypeEnum.DC_FIELD,
        ],
        "bess_device_type_ids": [],
    },
}
