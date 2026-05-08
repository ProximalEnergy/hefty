import datetime
from typing import Annotated

import pandas as pd
from core.crud.operational.kpi_data import core_get_kpi_data
from core.db_query import OutputType
from core.enumerations import KPITypeEnum
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import interfaces
from app.dependencies import get_async_db, get_project_api
from core import models

router = APIRouter(
    prefix="/bess-waterfall",
    tags=["project_bess_waterfall"],
)


def _efficiency(
    *,
    energy_before: float,
    energy_after: float,
    expected_efficiency: float,
) -> interfaces.EnergyLoss:
    """Compute energy loss and efficiency between before/after values.

    Args:
        energy_before: Energy at the upstream step.
        energy_after: Energy at the downstream step.
        expected_efficiency: Expected efficiency for this step.
    """
    if energy_before == 0:
        raise ValueError(
            "energy_before cannot be zero for efficiency calculation",
        )
    return interfaces.EnergyLoss(
        energy_loss=energy_after - energy_before,
        efficiency=energy_after / energy_before,
        expected_efficiency=expected_efficiency,
    )


@router.get(
    "",
    response_model=interfaces.ProjectBessWaterfallResponse,
    operation_id="get_project_bess_waterfall",
)
async def get_project_bess_waterfall(
    project: Annotated[models.Project, Depends(get_project_api)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    start: datetime.date = Query(..., description="Start date (inclusive)"),
    end: datetime.date = Query(..., description="End date (exclusive)"),
) -> interfaces.ProjectBessWaterfallResponse:
    """Return BESS energy waterfall values from operational KPI data.

    Args:
        project: Resolved project from path.
        db: Async DB session (operational schema).
        start: Start date for KPI aggregation.
        end: End date for KPI aggregation.
    """
    if not project.capacity_bess_energy_bol_dc:
        raise HTTPException(
            status_code=404,
            detail="Missing BESS energy capacity metadata for project",
        )
    project_charged_kpi = KPITypeEnum.BESS_PROJECT_ENERGY_CHARGED.value
    aux_energy_kpi = KPITypeEnum.BESS_MV_AUX_METER_ENERGY.value
    feeder_charged_kpi = KPITypeEnum.BESS_CIRCUIT_ENERGY_CHARGED.value
    string_charged_kpi = KPITypeEnum.BESS_STRING_ENERGY_CHARGED.value
    string_discharged_kpi = KPITypeEnum.BESS_STRING_ENERGY_DISCHARGED.value
    feeder_discharged_kpi = KPITypeEnum.BESS_CIRCUIT_ENERGY_DISCHARGED.value
    project_discharged_kpi = KPITypeEnum.PROJECT_ENERGY_DISCHARGED.value

    all_kpis = [
        project_charged_kpi,
        aux_energy_kpi,
        feeder_charged_kpi,
        string_charged_kpi,
        string_discharged_kpi,
        feeder_discharged_kpi,
        project_discharged_kpi,
    ]

    kpi_data = await core_get_kpi_data(
        start=start,
        end=end,
        project_ids=[project.project_id],
        kpi_type_ids=all_kpis,
        include_device_data=False,
    ).get_async(
        executor=db,
        output_type=OutputType.PANDAS,
    )

    if kpi_data.empty:
        raise HTTPException(status_code=404, detail="No KPI data found for range")

    kpi_data = kpi_data.set_index("date")

    series = []

    for kpi in all_kpis:
        series.append(kpi_data.loc[kpi_data.kpi_type_id == kpi, "project_data"])
    concat = pd.concat(series, axis=1)

    concat.columns = all_kpis

    concat = concat.dropna()

    energy_sum = concat.sum()

    if energy_sum.drop(aux_energy_kpi).min() < 3 * project.capacity_bess_energy_bol_dc:
        raise HTTPException(
            status_code=404,
            detail="Insufficient cycles (need at least 3× BOL capacity)",
        )

    charge_at_mv_circuits = energy_sum[feeder_charged_kpi] + energy_sum[aux_energy_kpi]

    try:
        return interfaces.ProjectBessWaterfallResponse(
            charge_at_poi=energy_sum[project_charged_kpi],
            gen_tie_gsu_step_down=_efficiency(
                energy_before=energy_sum[project_charged_kpi],
                energy_after=charge_at_mv_circuits,
                expected_efficiency=0.97,
            ),
            charge_at_mv_circuits=charge_at_mv_circuits,
            aux_energy=_efficiency(
                energy_before=charge_at_mv_circuits,
                energy_after=energy_sum[feeder_charged_kpi],
                expected_efficiency=0.99,
            ),
            charge_at_feeder=energy_sum[feeder_charged_kpi],
            mvt_step_down_pcs=_efficiency(
                energy_before=energy_sum[feeder_charged_kpi],
                energy_after=energy_sum[string_charged_kpi],
                expected_efficiency=0.95,
            ),
            charge_at_string=energy_sum[string_charged_kpi],
            rte=_efficiency(
                energy_before=energy_sum[string_charged_kpi],
                energy_after=energy_sum[string_discharged_kpi],
                expected_efficiency=0.90,
            ),
            discharge_at_string=energy_sum[string_discharged_kpi],
            pcs_pvt_step_up=_efficiency(
                energy_before=energy_sum[string_discharged_kpi],
                energy_after=energy_sum[feeder_discharged_kpi],
                expected_efficiency=0.95,
            ),
            discharge_at_feeder=energy_sum[feeder_discharged_kpi],
            gen_tie_gsu_step_up=_efficiency(
                energy_before=energy_sum[feeder_discharged_kpi],
                energy_after=energy_sum[project_discharged_kpi],
                expected_efficiency=0.97,
            ),
            discharge_at_poi=energy_sum[project_discharged_kpi],
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/aux-energy-daily-avg",
    response_model=interfaces.AuxEnergyDailyAvgResponse,
    operation_id="get_project_bess_aux_energy_daily_avg",
)
async def get_project_bess_aux_energy_daily_avg(
    project: Annotated[models.Project, Depends(get_project_api)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    start: datetime.date = Query(..., description="Start date (inclusive)"),
    end: datetime.date = Query(..., description="End date (exclusive)"),
) -> interfaces.AuxEnergyDailyAvgResponse:
    """Return average auxiliary energy per day (MWh) over the date range.

    Args:
        project: Resolved project from path.
        db: Async DB session (operational schema).
        start: Start date for KPI aggregation.
        end: End date for KPI aggregation.
    """
    aux_energy_kpi = KPITypeEnum.BESS_MV_AUX_METER_ENERGY.value
    kpi_data = await core_get_kpi_data(
        start=start,
        end=end,
        project_ids=[project.project_id],
        kpi_type_ids=[aux_energy_kpi],
        include_device_data=False,
    ).get_async(
        executor=db,
        output_type=OutputType.PANDAS,
    )
    if kpi_data.empty:
        raise HTTPException(status_code=404, detail="No aux KPI data found")
    kpi_data = kpi_data.dropna(subset=["project_data"])
    if kpi_data.empty:
        raise HTTPException(status_code=404, detail="No aux KPI data found")
    total_aux = float(kpi_data["project_data"].sum())
    days = max((end - start).days, 1)
    return interfaces.AuxEnergyDailyAvgResponse(
        average_aux_energy_per_day=total_aux / days,
    )
