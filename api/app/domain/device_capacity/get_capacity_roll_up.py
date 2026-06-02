from app.domain.device_capacity.base_capacity_roll_up import (
    BASE_ENERGY_CAPACITY_ROLL_UP,
    BASE_POWER_CAPACITY_AC_ROLL_UP,
    BASE_POWER_CAPACITY_DC_ROLL_UP,
)
from app.domain.device_capacity.exception import (
    ENERGY_CAPACITY_ROLL_UP_PER_PROJECT,
    POWER_AC_CAPACITY_ROLL_UP_PER_PROJECT,
    POWER_DC_CAPACITY_ROLL_UP_PER_PROJECT,
)
from core.enumerations import DeviceTypeEnum, ProjectID


def get_energy_capacity_roll_up(
    *,
    project_id: ProjectID,
) -> dict[DeviceTypeEnum, DeviceTypeEnum | None]:
    """Get the energy capacity roll-up map for a project.

    Args:
        project_id: Project identifier.
    """
    if project_id in ENERGY_CAPACITY_ROLL_UP_PER_PROJECT:
        return ENERGY_CAPACITY_ROLL_UP_PER_PROJECT[project_id]
    return BASE_ENERGY_CAPACITY_ROLL_UP


def get_power_ac_capacity_roll_up(
    *,
    project_id: ProjectID,
) -> dict[DeviceTypeEnum, DeviceTypeEnum | None]:
    """Get the AC power capacity roll-up map for a project.

    Args:
        project_id: Project identifier.
    """
    if project_id in POWER_AC_CAPACITY_ROLL_UP_PER_PROJECT:
        return POWER_AC_CAPACITY_ROLL_UP_PER_PROJECT[project_id]
    return BASE_POWER_CAPACITY_AC_ROLL_UP


def get_power_dc_capacity_roll_up(
    *,
    project_id: ProjectID,
) -> dict[DeviceTypeEnum, DeviceTypeEnum | None]:
    """Get the DC power capacity roll-up map for a project.

    Args:
        project_id: Project identifier.
    """
    if project_id in POWER_DC_CAPACITY_ROLL_UP_PER_PROJECT:
        return POWER_DC_CAPACITY_ROLL_UP_PER_PROJECT[project_id]
    return BASE_POWER_CAPACITY_DC_ROLL_UP
