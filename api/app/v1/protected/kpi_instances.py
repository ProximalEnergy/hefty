import uuid
from typing import Annotated

from core.enumerations import KPIType, ProjectType
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, utils
from app._crud.operational.kpi_instances import (
    bulk_delete_kpi_instances,
    bulk_upsert_kpi_instances,
)
from core import models


class KPITypeInstance(BaseModel):
    """KPI type instance metadata."""

    kpi_type_id: KPIType
    metric_name: str
    device_type_id: int
    device_type_name_long: str
    project_type_id: int | None


class KPIInstanceColumn(BaseModel):
    """KPI instance column metadata."""

    name_long: str
    project_type_id: int
    has_any_kpi_instances: bool


class KPIInstanceData(BaseModel):
    """KPI instance data structure."""

    rows: list[KPITypeInstance]
    columns: dict[uuid.UUID, KPIInstanceColumn]
    data: dict[str, bool]  # in the form "<kpi_type_id>::<project_id>" -> bool


router = APIRouter(
    prefix="/kpi-instances",
    tags=["kpi-instances"],
    include_in_schema=utils.get_include_in_schema(),
    dependencies=[Depends(dependencies.requires_superadmin_async)],
)


def _parse_kpi_instance_key(*, key: str) -> tuple[int, uuid.UUID]:
    """Parse KPI instance key in '<kpi_type_id>::<project_id>' format.

    Args:
        key: Composite KPI instance key.
    """
    parts = key.split("::", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid key format: {key}")

    try:
        kpi_type_id = int(parts[0])
        project_id = uuid.UUID(parts[1])
    except ValueError as exc:
        raise ValueError(f"Invalid key format: {key}") from exc

    return kpi_type_id, project_id


@router.get("/")
async def get_kpi_instances(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
) -> KPIInstanceData:
    """Get KPI instance data for all projects and KPI types.

    Queries projects, KPI types, and KPI instances separately, then builds
    response data containing all projects and KPI types and instance visibility
    where available.
    """
    # Query all projects
    projects_stmt = (
        select(
            models.Project.project_id,
            models.Project.name_long.label("project_name_long"),
            models.Project.project_type_id,
            func.count(models.KPIInstance.project_id).label("kpi_instance_count"),
        )
        .outerjoin(
            models.KPIInstance,
            models.Project.project_id == models.KPIInstance.project_id,
        )
        .group_by(
            models.Project.project_id,
            models.Project.name_long,
            models.Project.project_type_id,
        )
        .order_by(models.Project.project_type_id, models.Project.name_long)
    )
    projects_result = await db.execute(projects_stmt)
    project_rows = projects_result.all()

    # Build columns from all projects
    projects_dict: dict[uuid.UUID, KPIInstanceColumn] = {}
    for row in project_rows:
        projects_dict[row.project_id] = KPIInstanceColumn(
            name_long=row.project_name_long,
            project_type_id=row.project_type_id,
            has_any_kpi_instances=row.kpi_instance_count > 0,
        )
    columns: dict[uuid.UUID, KPIInstanceColumn] = projects_dict

    # Query all KPI types
    kpi_types_stmt = (
        select(
            models.KPIType.kpi_type_id,
            models.KPIType.name_metric,
            models.KPIType.device_type_id,
            models.DeviceType.name_long.label("device_type_name_long"),
        )
        .join(
            models.DeviceType,
            models.KPIType.device_type_id == models.DeviceType.device_type_id,
        )
        .order_by(models.DeviceType.name_long, models.KPIType.name_metric)
    )
    kpi_types_result = await db.execute(kpi_types_stmt)
    kpi_type_rows = kpi_types_result.all()

    # Query all KPI instances
    instances_stmt = select(
        models.KPIInstance.kpi_type_id,
        models.KPIInstance.project_id,
        models.KPIInstance.is_visible,
    )
    instances_result = await db.execute(instances_stmt)
    instance_rows = instances_result.all()

    # Map project types present per KPI type from existing instances.
    project_type_by_project_id = {
        row.project_id: int(row.project_type_id) for row in project_rows
    }
    kpi_type_has_pv: dict[int, bool] = {}
    kpi_type_has_bess: dict[int, bool] = {}
    kpi_type_has_pvs: dict[int, bool] = {}
    for instance_row in instance_rows:
        kpi_type_id = int(instance_row.kpi_type_id)
        project_type_id = project_type_by_project_id.get(instance_row.project_id)
        if project_type_id is None:
            continue
        if project_type_id == int(ProjectType.PV):
            kpi_type_has_pv[kpi_type_id] = True
        elif project_type_id == int(ProjectType.BESS):
            kpi_type_has_bess[kpi_type_id] = True
        elif project_type_id == int(ProjectType.PVS):
            kpi_type_has_pvs[kpi_type_id] = True

    # Build rows: list[KPITypeInstance] from all KPI types
    rows: list[KPITypeInstance] = []
    for kpi_type_row in kpi_type_rows:
        kpi_type_id = int(kpi_type_row.kpi_type_id)
        kpi_type_enum = KPIType(kpi_type_id)
        has_pv = kpi_type_has_pv.get(kpi_type_id, False)
        has_bess = kpi_type_has_bess.get(kpi_type_id, False)
        has_pvs = kpi_type_has_pvs.get(kpi_type_id, False)
        row_project_type_id: int | None
        if has_pv and has_bess:
            row_project_type_id = int(ProjectType.PVS)
        elif has_bess:
            row_project_type_id = int(ProjectType.BESS)
        elif has_pv:
            row_project_type_id = int(ProjectType.PV)
        elif has_pvs:
            row_project_type_id = int(ProjectType.PVS)
        else:
            row_project_type_id = None
        rows.append(
            KPITypeInstance(
                kpi_type_id=kpi_type_enum,
                metric_name=str(kpi_type_row.name_metric),
                device_type_id=int(kpi_type_row.device_type_id),
                device_type_name_long=str(kpi_type_row.device_type_name_long),
                project_type_id=row_project_type_id,
            )
        )

    # Build data as flat map: "<kpi_type_id>::<project_id>" -> is_visible
    data: dict[str, bool] = {}
    for instance_row in instance_rows:
        key = f"{instance_row.kpi_type_id}::{instance_row.project_id}"
        data[key] = bool(instance_row.is_visible)

    return KPIInstanceData(rows=rows, columns=columns, data=data)


@router.post("/upsert")
async def upsert_kpi_instances(
    data: dict[str, bool],
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
) -> dict[str, int]:
    """Upsert KPI instances by composite key.

    Args:
        data: Mapping of '<kpi_type_id>::<project_id>' to is_visible.
        db: Async database session.
    """
    parsed_rows: list[tuple[int, uuid.UUID, bool]] = []
    for key, is_visible in data.items():
        try:
            kpi_type_id, project_id = _parse_kpi_instance_key(key=key)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        parsed_rows.append((kpi_type_id, project_id, bool(is_visible)))

    try:
        upserted = await bulk_upsert_kpi_instances(db=db, rows=parsed_rows)
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to upsert KPI instances.",
        ) from exc

    return {"processed": len(parsed_rows), "upserted": upserted}


@router.post("/delete")
async def delete_kpi_instances(
    keys: list[str],
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
) -> dict[str, int]:
    """Delete KPI instances by composite keys.

    Args:
        keys: List of '<kpi_type_id>::<project_id>' strings.
        db: Async database session.
    """
    parsed_keys: list[tuple[int, uuid.UUID]] = []
    for key in keys:
        try:
            parsed_keys.append(_parse_kpi_instance_key(key=key))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        deleted = await bulk_delete_kpi_instances(db=db, keys=parsed_keys)
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to delete KPI instances.",
        ) from exc

    return {"processed": len(parsed_keys), "deleted": deleted}
