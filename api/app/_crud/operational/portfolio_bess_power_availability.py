"""Aggregate latest PCS power availability for many projects in one query."""

import asyncio
import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

import core.models as models
import pandas as pd
from core.crud.project.devices import get_project_devices
from core.db_query import OutputType
from core.enumerations import DeviceTypeEnum, SensorTypeEnum
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _numeric_from_operational_row(
    *,
    row: models.OperationalDataTimeseries,
) -> float:
    """Return the first non-null numeric column as float (matches web getValue)."""
    for attr in (
        "value_double",
        "value_real",
        "value_bigint",
        "value_integer",
    ):
        v = getattr(row, attr, None)
        if v is not None:
            return float(v)
    return 0.0


@dataclass
class PortfolioBessPowerAvailabilityMetrics:
    """Portfolio power availability metrics for one project."""

    available_power_mw: float | None
    poi_capacity_mw: float | None
    max_pcs_capacity_mw: float | None
    num_pcs_units: int | None
    power_availability_pct_poi: float | None
    power_availability_pct_pcs: float | None


async def _get_pcs_capacity_metrics(
    *,
    project_schema: str,
) -> tuple[float | None, int | None]:
    """Return cumulative PCS AC capacity and unit count for one project.

    Args:
        project_schema: Project schema name_short.
    """
    devices_df = await get_project_devices(
        device_type_ids=[DeviceTypeEnum.BESS_PCS],
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    if devices_df.empty:
        return None, None

    capacity_series = pd.to_numeric(devices_df["capacity_ac"], errors="coerce").fillna(
        0
    )
    total_capacity_mw = float(capacity_series.sum()) / 1000
    return total_capacity_mw if total_capacity_mw > 0 else None, int(len(devices_df))


async def get_portfolio_bess_power_availability_metrics(
    *,
    db: AsyncSession,
    project_ids: Sequence[uuid.UUID],
    poi_by_project: dict[uuid.UUID, float | None],
    project_schema_by_id: dict[uuid.UUID, str],
) -> dict[uuid.UUID, PortfolioBessPowerAvailabilityMetrics]:
    """Compute realtime power availability % per project from operational TS.

    Uses PostgreSQL DISTINCT ON over operational.data_timeseries so each
    (project_id, tag_id) contributes only its latest row for PCS available
    charge/discharge power sensors. Matches useRealtimePowerAvailability.

    Args:
        db: Async session for the operational database.
        project_ids: Projects to load (caller enforces access).
        poi_by_project: POI limit in MW per project_id.
        project_schema_by_id: Project schema name_short per project_id.

    Returns:
        Map project_id → aggregate power availability metrics.
    """
    ids = list(project_ids)
    if not ids:
        return {}

    stmt = (
        select(models.OperationalDataTimeseries)
        .distinct(
            models.OperationalDataTimeseries.project_id,
            models.OperationalDataTimeseries.tag_id,
        )
        .where(
            models.OperationalDataTimeseries.project_id.in_(ids),
            models.OperationalDataTimeseries.sensor_type_id.in_(
                [
                    int(SensorTypeEnum.BESS_PCS_AVAILABLE_CHARGE_POWER),
                    int(SensorTypeEnum.BESS_PCS_AVAILABLE_DISCHARGE_POWER),
                ],
            ),
        )
        .order_by(
            models.OperationalDataTimeseries.project_id,
            models.OperationalDataTimeseries.tag_id,
            models.OperationalDataTimeseries.time.desc(),
        )
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    charge_sum: dict[uuid.UUID, float] = defaultdict(float)
    discharge_sum: dict[uuid.UUID, float] = defaultdict(float)
    seen: set[uuid.UUID] = set()

    charge_id = int(SensorTypeEnum.BESS_PCS_AVAILABLE_CHARGE_POWER)
    discharge_id = int(SensorTypeEnum.BESS_PCS_AVAILABLE_DISCHARGE_POWER)

    for row in rows:
        pid = row.project_id
        seen.add(pid)
        v = _numeric_from_operational_row(row=row)
        if row.sensor_type_id == charge_id:
            charge_sum[pid] += v
        elif row.sensor_type_id == discharge_id:
            discharge_sum[pid] += v

    pcs_capacity_results = await asyncio.gather(
        *[
            _get_pcs_capacity_metrics(project_schema=project_schema_by_id[pid])
            for pid in ids
            if pid in project_schema_by_id
        ]
    )
    pcs_capacity_by_project = dict(
        zip(
            [pid for pid in ids if pid in project_schema_by_id],
            pcs_capacity_results,
            strict=False,
        )
    )

    out: dict[uuid.UUID, PortfolioBessPowerAvailabilityMetrics] = {}
    for pid in ids:
        poi = poi_by_project.get(pid)
        max_pcs_capacity_mw, num_pcs_units = pcs_capacity_by_project.get(
            pid, (None, None)
        )
        max_available = None
        if pid in seen:
            max_available = max(abs(charge_sum[pid]), abs(discharge_sum[pid]))

        pct_poi = None
        if max_available is not None and poi is not None and poi > 0:
            pct_poi = min((max_available / poi) * 100.0, 100.0)

        pct_pcs = None
        if (
            max_available is not None
            and max_pcs_capacity_mw is not None
            and max_pcs_capacity_mw > 0
        ):
            pct_pcs = min((max_available / max_pcs_capacity_mw) * 100.0, 100.0)

        out[pid] = PortfolioBessPowerAvailabilityMetrics(
            available_power_mw=max_available,
            poi_capacity_mw=poi,
            max_pcs_capacity_mw=max_pcs_capacity_mw,
            num_pcs_units=num_pcs_units,
            power_availability_pct_poi=pct_poi,
            power_availability_pct_pcs=pct_pcs,
        )

    return out
