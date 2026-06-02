from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy.engine import CursorResult
from sqlalchemy.sql.dml import Update

from core import models
from core.database import with_db
from core.enumerations import DeviceTypeEnum, ProjectID
from app.domain.device_capacity.get_capacity_roll_up import get_energy_capacity_roll_up, get_power_ac_capacity_roll_up, get_power_dc_capacity_roll_up


def get_parent_capacity_energy_update_stmt(
    child_device_type: DeviceTypeEnum,
    parent_device_types: list[DeviceTypeEnum],
    capacity_column: str,
) -> Update:
    """Build a statement to roll child capacity up to ancestors.

    Returns:
        SQLAlchemy update statement.
    """
    device_table = cast(sa.Table, models.Device.__table__)
    child = device_table.alias("child")
    parent_totals = device_table.alias("parent_totals")

    totals = (
        sa.select(
            parent_totals.c.device_id,
            sa.func.sum(child.c[capacity_column]).label(capacity_column),
        )
        .select_from(
            child.join(
                parent_totals,
                parent_totals.c.device_id_path.op("@>")(child.c.device_id_path),
            ),
        )
        .where(child.c.device_type_id == child_device_type.value)
        .where(
            parent_totals.c.device_type_id.in_(
                [device_type.value for device_type in parent_device_types],
            ),
        )
        .group_by(parent_totals.c.device_id)
        .subquery("totals")
    )

    return (
        sa.update(device_table)
        .where(device_table.c.device_id == totals.c.device_id)
        .values({capacity_column: totals.c[capacity_column]})
    )

def get_roll_up_stmts(map: dict[DeviceTypeEnum, DeviceTypeEnum | None], capacity_column: str) -> list[Update]:
    stmts = []
    for child_device in set(map.values()):
        if child_device is None:
            continue
        parent_devices = [parent for parent, child in map.items() if child == child_device]
        stmts.append(get_parent_capacity_energy_update_stmt(
            child_device_type=child_device,
            parent_device_types=parent_devices,
            capacity_column=capacity_column,
        ))
    return stmts

def run_roll_up_capacities(project_id: ProjectID):

    stmts = []
    updated_rows = 0

    stmts.extend(get_roll_up_stmts(get_power_ac_capacity_roll_up(project_id=project_id), models.Device.capacity_power_ac_kw.name))
    stmts.extend(get_roll_up_stmts(get_power_dc_capacity_roll_up(project_id=project_id), models.Device.capacity_power_dc_kw.name))
    stmts.extend(get_roll_up_stmts(get_energy_capacity_roll_up(project_id=project_id), models.Device.capacity_energy_dc_kwh.name))

    with with_db(schema=project_id.name.lower()) as db:
        for stmt in stmts:
            result = cast(CursorResult[Any], db.execute(stmt))
            updated_rows += result.rowcount or 0
        db.commit()

    print(f"{project_id.name.lower()}: updated {updated_rows} rows")

