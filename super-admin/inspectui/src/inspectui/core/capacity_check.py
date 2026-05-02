"""Capacity-field requirements for project-schema devices."""

from dataclasses import dataclass

from core.enumerations import DeviceTypeEnum

from core import models
from inspectui.core.models import DeviceInfo

capacity_dc = models.Device.capacity_dc.name
capacity_ac = models.Device.capacity_ac.name
capacity_energy_dc = models.Device.capacity_energy_dc.name

CapacityFieldName = str


@dataclass(frozen=True)
class CapacityRequirement:
    """A device type and capacity field that must be populated."""

    device_type: DeviceTypeEnum
    field_name: CapacityFieldName

    @property
    def device_type_label(self) -> str:
        """Return a compact device type label."""
        return f"{self.device_type.name.lower()} ({self.device_type.value})"


@dataclass(frozen=True)
class MissingCapacityDevice:
    """Device missing a required capacity field."""

    device_id: int
    name_short: str | None
    name_long: str | None

    @property
    def display_name(self) -> str:
        """Return the best available device label."""
        return self.name_short or self.name_long or f"device {self.device_id}"


@dataclass(frozen=True)
class CapacityCheckRow:
    """Result for one device type and required capacity field."""

    requirement: CapacityRequirement
    checked_count: int
    missing_devices: tuple[MissingCapacityDevice, ...]

    @property
    def passed(self) -> bool:
        """Return True when all matching devices have the field populated."""
        return len(self.missing_devices) == 0

    @property
    def missing_count(self) -> int:
        """Return the number of devices missing this field."""
        return len(self.missing_devices)


CAPACITY_REQUIREMENTS: tuple[CapacityRequirement, ...] = (
    CapacityRequirement(DeviceTypeEnum.PV_INVERTER, capacity_dc),
    CapacityRequirement(DeviceTypeEnum.PV_INVERTER, capacity_ac),
    CapacityRequirement(DeviceTypeEnum.PV_INVERTER_MODULE, capacity_dc),
    CapacityRequirement(DeviceTypeEnum.PV_INVERTER_MODULE, capacity_ac),
    CapacityRequirement(DeviceTypeEnum.METER, capacity_ac),
    CapacityRequirement(DeviceTypeEnum.PV_BLOCK, capacity_dc),
    CapacityRequirement(DeviceTypeEnum.PV_BLOCK, capacity_ac),
    CapacityRequirement(DeviceTypeEnum.PPC, capacity_ac),
    CapacityRequirement(DeviceTypeEnum.BESS_BLOCK, capacity_ac),
    CapacityRequirement(DeviceTypeEnum.BESS_PCS, capacity_ac),
    CapacityRequirement(DeviceTypeEnum.PV_MVT, capacity_dc),
    CapacityRequirement(DeviceTypeEnum.PV_MVT, capacity_ac),
    CapacityRequirement(DeviceTypeEnum.PV_MV_COLLECTOR_CIRCUIT, capacity_ac),
    CapacityRequirement(DeviceTypeEnum.BESS_MV_COLLECTOR_CIRCUIT, capacity_ac),
    CapacityRequirement(
        DeviceTypeEnum.PV_MV_COLLECTOR_CIRCUIT_METER,
        capacity_ac,
    ),
    CapacityRequirement(
        DeviceTypeEnum.BESS_MV_COLLECTOR_CIRCUIT_METER,
        capacity_ac,
    ),
    CapacityRequirement(DeviceTypeEnum.BESS_MV_AUX_METER, capacity_ac),
    CapacityRequirement(DeviceTypeEnum.PV_FEEDER, capacity_ac),
    CapacityRequirement(DeviceTypeEnum.BESS_FEEDER, capacity_ac),
    CapacityRequirement(DeviceTypeEnum.BESS_MVT, capacity_ac),
    CapacityRequirement(DeviceTypeEnum.BESS_STRING, capacity_dc),
    CapacityRequirement(DeviceTypeEnum.BESS_STRING, capacity_energy_dc),
    CapacityRequirement(DeviceTypeEnum.DC_FIELD, capacity_dc),
    CapacityRequirement(DeviceTypeEnum.BESS_CELL, capacity_energy_dc),
    CapacityRequirement(DeviceTypeEnum.BESS_PCS_MODULE_GROUP, capacity_ac),
    CapacityRequirement(DeviceTypeEnum.BESS_PCS_MODULE, capacity_ac),
    CapacityRequirement(DeviceTypeEnum.BESS_MODULE, capacity_energy_dc),
)


def check_capacity_requirements(
    *,
    devices: list[DeviceInfo],
) -> list[CapacityCheckRow]:
    """Check devices against the required capacity-field matrix.

    Args:
        devices: Device rows fetched from `core.models.Device`.

    Returns:
        One result row per required device type and capacity field.
    """
    rows: list[CapacityCheckRow] = []
    for requirement in CAPACITY_REQUIREMENTS:
        matching = [
            device
            for device in devices
            if device.device_type_id == requirement.device_type.value
        ]
        missing = tuple(
            MissingCapacityDevice(
                device_id=device.device_id,
                name_short=device.name_short,
                name_long=device.name_long,
            )
            for device in matching
            if getattr(device, requirement.field_name) is None
        )
        rows.append(
            CapacityCheckRow(
                requirement=requirement,
                checked_count=len(matching),
                missing_devices=missing,
            )
        )
    return rows
