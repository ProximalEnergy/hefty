"""Git-tracked shared test defaults using core enumerations."""

from typing import Any

from core.enumerations import DeviceType, SensorType

TEST_PARAMS: dict[str, dict[str, Any]] = {
    "sensor_type_unique_per_device": {
        "sensor_type_ids": [
            SensorType.BESS_STRING_DISCHARGE_ENERGY_TOTAL,
            SensorType.BESS_STRING_CHARGE_ENERGY_TOTAL,
        ],
    },
    "parent_device_type_allowlist": {
        "child_parent_type_rules": {
            # ===== PV =====
            DeviceType.DC_FIELD: [DeviceType.PV_DC_COMBINER],
            DeviceType.PV_DC_COMBINER: [
                DeviceType.PV_INVERTER_MODULE,
                DeviceType.PV_INVERTER,
            ],
            DeviceType.PV_INVERTER_MODULE: [DeviceType.PV_INVERTER],
            DeviceType.PV_INVERTER: [DeviceType.PV_MVT],
            DeviceType.PV_MVT: [DeviceType.PV_BLOCK],
            DeviceType.TRACKER_ROW: [DeviceType.TRACKER_ZONE],
            DeviceType.TRACKER_ZONE: [DeviceType.PV_BLOCK],
            DeviceType.MET_STATION: [DeviceType.PV_BLOCK],
            DeviceType.PV_BLOCK: [
                # If there is MV/HV equipment, Blocks will map to Feeders
                DeviceType.PV_FEEDER,
                # No Feeders: Blocks map to MV Collector Circuits
                DeviceType.PV_MV_COLLECTOR_CIRCUIT,
                # If there is not MV/HV equipment, Blocks will map to the PPC
                DeviceType.PPC,
            ],
            DeviceType.PV_FEEDER: [
                # If there are MV Collector Circuits, Feeders will map to Circuits
                DeviceType.PV_MV_COLLECTOR_CIRCUIT,
                # If there are not MV Collector Circuits, Feeders will map to the PPC
                DeviceType.PPC,
            ],
            DeviceType.PV_MV_COLLECTOR_CIRCUIT: [
                # If there are MV Collector Circuit Meters, Circuits will map to Meters
                DeviceType.PV_MV_COLLECTOR_CIRCUIT_METER,
                # No MV Collector Circuit Meters: Circuits map to PPC
                DeviceType.PPC,
            ],
            DeviceType.PV_MV_COLLECTOR_CIRCUIT_METER: [DeviceType.PPC],
            # ===== BESS =====
            DeviceType.BESS_CELL: [DeviceType.BESS_MODULE],
            DeviceType.BESS_MODULE: [DeviceType.BESS_STRING],
            DeviceType.BESS_STRING: [DeviceType.BESS_ENCLOSURE],
            DeviceType.BESS_ENCLOSURE: [
                # If there are Banks, Enclosures will map to Banks
                DeviceType.BESS_BANK,
                # If there are not Banks, Enclosures will map to PCS Module Groups
                DeviceType.BESS_PCS_MODULE_GROUP,
                # If there are not PCS Module Groups, Enclosures will map to PCS Modules
                DeviceType.BESS_PCS_MODULE,
                # If there are not PCS Modules, Enclosures will map to PCSs
                DeviceType.BESS_PCS,
            ],
            DeviceType.BESS_BANK: [
                # If there are PCS Module Groups, Banks will map to Module Groups
                DeviceType.BESS_PCS_MODULE_GROUP,
                # If there are not Module Groups, Banks will map to PCS Modules
                DeviceType.BESS_PCS_MODULE,
            ],
            DeviceType.BESS_PCS_MODULE: [
                # If there are PCS Module Groups, PCS Modules will map to Module Groups
                DeviceType.BESS_PCS_MODULE_GROUP,
                # No PCS Module Groups: PCS Modules map to BESS DC Skid
                DeviceType.BESS_DC_SKID,
            ],
            DeviceType.BESS_PCS_MODULE_GROUP: [DeviceType.BESS_DC_SKID],
            DeviceType.BESS_DC_SKID: [DeviceType.BESS_PCS],
            DeviceType.BESS_PCS: [DeviceType.BESS_MVT],
            DeviceType.BESS_MVT: [DeviceType.BESS_BLOCK],
            DeviceType.BESS_BLOCK: [
                # If there is MV/HV equipment, Blocks will map to Feeders
                DeviceType.BESS_FEEDER,
                # No Feeders: Blocks map to MV Collector Circuits
                DeviceType.BESS_MV_COLLECTOR_CIRCUIT,
                # If there is not MV/HV equipment, Blocks will map to the PPC
                DeviceType.PPC,
            ],
            DeviceType.BESS_FEEDER: [DeviceType.BESS_MV_COLLECTOR_CIRCUIT],
            DeviceType.BESS_MV_COLLECTOR_CIRCUIT: [
                DeviceType.BESS_MV_COLLECTOR_CIRCUIT_METER
            ],
            DeviceType.BESS_MV_COLLECTOR_CIRCUIT_METER: [DeviceType.PPC],
            # ===== SYSTEM =====
            DeviceType.PPC: [DeviceType.METER],
            DeviceType.METER: [DeviceType.PROJECT],
        },
    },
    "required_device_models": {
        "device_type_ids": [
            DeviceType.PV_INVERTER,
        ],
    },
}
