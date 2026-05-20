from typing import Any, cast

import sqlalchemy as sa
from pydantic import BaseModel
from sqlalchemy.engine import CursorResult
from sqlalchemy.sql.dml import Update

from core import models
from core.database import with_db
from core.enumerations import DeviceTypeEnum, ProjectID


project_ids: list[ProjectID] | None = [ProjectID.MASON_INDIE]

if project_ids is None:
    project_ids = list(ProjectID)


class ParentCapacityUpdate(BaseModel):
    """Parameters for a parent capacity rollup update."""

    child_device_type: DeviceTypeEnum
    parent_device_types: list[DeviceTypeEnum]
    capacity_column: str


UPDATES = [
    # energy capacity
    ParentCapacityUpdate(
        child_device_type=DeviceTypeEnum.BESS_STRING,
        parent_device_types=[
            DeviceTypeEnum.BESS_ENCLOSURE,
            DeviceTypeEnum.BESS_BANK,
            DeviceTypeEnum.BESS_PCS_MODULE,
            DeviceTypeEnum.BESS_PCS_MODULE_GROUP,
            DeviceTypeEnum.BESS_DC_SKID,
            DeviceTypeEnum.BESS_PCS,
            DeviceTypeEnum.BESS_MVT,
            DeviceTypeEnum.BESS_BLOCK,
            DeviceTypeEnum.BESS_FEEDER,
            DeviceTypeEnum.BESS_MV_COLLECTOR_CIRCUIT_METER,
            DeviceTypeEnum.PPC,
            DeviceTypeEnum.METER,
            DeviceTypeEnum.PROJECT,
        ],
        capacity_column=models.Device.capacity_energy_dc_kwh.name,
    ),
    # power capacity
    ParentCapacityUpdate(
        child_device_type=DeviceTypeEnum.BESS_PCS_MODULE,
        parent_device_types=[
            DeviceTypeEnum.BESS_PCS_MODULE_GROUP,
            DeviceTypeEnum.BESS_DC_SKID,
            DeviceTypeEnum.BESS_PCS,
        ],
        capacity_column=models.Device.capacity_power_ac_kw.name,
    ),
    ParentCapacityUpdate(
        child_device_type=DeviceTypeEnum.PV_INVERTER_MODULE,
        parent_device_types=[],
        capacity_column=models.Device.capacity_power_ac_kw.name,
    ),
    ParentCapacityUpdate(
        child_device_type=DeviceTypeEnum.PV_INVERTER,
        parent_device_types=[],
        capacity_column=models.Device.capacity_power_ac_kw.name,
    ),
    ParentCapacityUpdate(
        child_device_type=DeviceTypeEnum.BESS_MVT,
        parent_device_types=[
            DeviceTypeEnum.BESS_BLOCK,
            DeviceTypeEnum.BESS_FEEDER,
            DeviceTypeEnum.BESS_MV_COLLECTOR_CIRCUIT_METER,
        ],
        capacity_column=models.Device.capacity_power_ac_kw.name,
    ),
    ParentCapacityUpdate(
        child_device_type=DeviceTypeEnum.PPC,
        parent_device_types=[
            DeviceTypeEnum.METER,
            DeviceTypeEnum.PROJECT,
        ],
        capacity_column=models.Device.capacity_power_ac_kw.name,
    ),

    # dc power capacity
    ParentCapacityUpdate(
        child_device_type=DeviceTypeEnum.DC_FIELD,
        parent_device_types=[
            DeviceTypeEnum.PV_DC_COMBINER,
            DeviceTypeEnum.PV_INVERTER_MODULE,
            DeviceTypeEnum.PV_INVERTER,
            DeviceTypeEnum.PV_MVT,
            DeviceTypeEnum.PV_BLOCK,
            DeviceTypeEnum.PV_FEEDER,
            DeviceTypeEnum.PV_MV_COLLECTOR_CIRCUIT,
            DeviceTypeEnum.PV_MV_COLLECTOR_CIRCUIT_METER,
            DeviceTypeEnum.PPC,
            DeviceTypeEnum.METER,
            DeviceTypeEnum.PROJECT,
        ],
        capacity_column=models.Device.capacity_power_dc_kw.name,
    ),
    # ac power capacity
    ParentCapacityUpdate(
        child_device_type=DeviceTypeEnum.PV_MVT,
        parent_device_types=[
            DeviceTypeEnum.PV_BLOCK,
            DeviceTypeEnum.PV_FEEDER,
            DeviceTypeEnum.PV_MV_COLLECTOR_CIRCUIT,
            DeviceTypeEnum.PV_MV_COLLECTOR_CIRCUIT_METER,
        ],
        capacity_column=models.Device.capacity_power_ac_kw.name,
    ),
]


def get_parent_capacity_energy_update_stmt(
    update: ParentCapacityUpdate,
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
            sa.func.sum(child.c[update.capacity_column]).label(update.capacity_column),
        )
        .select_from(
            child.join(
                parent_totals,
                parent_totals.c.device_id_path.op("@>")(child.c.device_id_path),
            ),
        )
        .where(child.c.device_type_id == update.child_device_type.value)
        .where(
            parent_totals.c.device_type_id.in_(
                [device_type.value for device_type in update.parent_device_types],
            ),
        )
        .group_by(parent_totals.c.device_id)
        .subquery("totals")
    )

    return (
        sa.update(device_table)
        .where(device_table.c.device_id == totals.c.device_id)
        .values({update.capacity_column: totals.c[update.capacity_column]})
    )


def run_roll_up_capacities(project_ids: list[ProjectID]):
    total_updated_rows = 0

    for project_id in project_ids:
        project_updated_rows = 0

        with with_db(schema=project_id.name.lower()) as db:
            for update in UPDATES:
                stmt = get_parent_capacity_energy_update_stmt(update=update)
                result = cast(CursorResult[Any], db.execute(stmt))
                project_updated_rows += result.rowcount or 0
            db.commit()

        total_updated_rows += project_updated_rows
        print(f"{project_id.name.lower()}: updated {project_updated_rows} rows")

    print(f"Total rows updated: {total_updated_rows}")

if __name__ == "__main__":
    run_roll_up_capacities(project_ids=project_ids)
