import datetime
from uuid import UUID

import numpy as np

from core.crud.operational.kpi_data import get_kpi_data as crud_get_kpi_data
from core.crud.operational.projects import get_projects as crud_get_projects
from core.db_query import OutputType


async def get_project_rte(
    *,
    project_ids: list[UUID],
    start: datetime.date,
    end: datetime.date,
) -> dict[UUID, float | None]:
    """
    Get the RTE for a project.

    Args:
        project_ids: The project IDs to get the RTE for.
        start: The start date of the period.
        end: The end date of the period (exclusive).

    Returns:
        A dictionary of project IDs to RTE values.
    """
    STRING_ENERGY_CHARGED_KPI_ID = 37
    STRING_ENERGY_DISCHARGED_KPI_ID = 41
    PROJECT_SOC_INCREASE_KPI_ID = 94
    PROJECT_SOC_DECREASE_KPI_ID = 95

    THRESHOLD = 0.2

    projects = await crud_get_projects(project_ids=project_ids).get_async(
        output_type=OutputType.SQLALCHEMY
    )

    df = await crud_get_kpi_data(
        start=start,
        end=end,
        project_ids=[project.project_id for project in projects],
        kpi_type_ids=[
            STRING_ENERGY_CHARGED_KPI_ID,
            STRING_ENERGY_DISCHARGED_KPI_ID,
            PROJECT_SOC_INCREASE_KPI_ID,
            PROJECT_SOC_DECREASE_KPI_ID,
        ],
        include_device_data=False,
    ).get_async(output_type=OutputType.PANDAS)

    rte_dict: dict[UUID, float | None] = {}

    for project in projects:
        if project.name_short is None:
            continue

        project_key = project.project_id
        rte_dict[project_key] = None

        project_df = df[df["project_id"] == project.project_id].copy()
        if project_df.empty:
            continue

        pivot_df = project_df.pivot(
            index="date",
            columns="kpi_type_id",
            values="project_data",
        ).reindex(
            columns=[
                STRING_ENERGY_CHARGED_KPI_ID,
                STRING_ENERGY_DISCHARGED_KPI_ID,
                PROJECT_SOC_INCREASE_KPI_ID,
                PROJECT_SOC_DECREASE_KPI_ID,
            ]
        )

        energy_cols = [STRING_ENERGY_CHARGED_KPI_ID, STRING_ENERGY_DISCHARGED_KPI_ID]
        pivot_df[energy_cols] = (
            pivot_df[energy_cols] / project.capacity_bess_energy_bol_dc
        )
        pivot_df = pivot_df.dropna()

        sum_df = pivot_df.sum(min_count=1)

        charge_total = sum_df[STRING_ENERGY_CHARGED_KPI_ID]
        if charge_total < THRESHOLD:
            charge_total = np.nan
        discharge_total = sum_df[STRING_ENERGY_DISCHARGED_KPI_ID]
        if discharge_total < THRESHOLD:
            discharge_total = np.nan
        soc_increase_total = sum_df[PROJECT_SOC_INCREASE_KPI_ID]
        if soc_increase_total < THRESHOLD:
            soc_increase_total = np.nan
        soc_decrease_total = sum_df[PROJECT_SOC_DECREASE_KPI_ID]
        if soc_decrease_total < THRESHOLD:
            soc_decrease_total = np.nan

        charge_efficiency = soc_increase_total / charge_total
        discharge_efficiency = discharge_total / soc_decrease_total
        rte = charge_efficiency * discharge_efficiency
        if rte > 1:
            rte = np.nan
        rte_dict[project_key] = rte

    return rte_dict
