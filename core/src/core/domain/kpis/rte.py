import datetime
from typing import Literal, cast
from uuid import UUID

import numpy as np
import pandas as pd

import core.models as models
from core.crud.operational.kpi_data import core_get_kpi_data as crud_get_kpi_data
from core.crud.operational.projects import get_projects as crud_get_projects
from core.db_query import OutputType
from core.enumerations import KPITypeEnum


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
    STRING_ENERGY_CHARGED_KPI_ID = KPITypeEnum.BESS_STRING_ENERGY_CHARGED.value
    STRING_ENERGY_DISCHARGED_KPI_ID = KPITypeEnum.BESS_STRING_ENERGY_DISCHARGED.value
    PROJECT_SOC_INCREASE_KPI_ID = KPITypeEnum.BESS_PROJECT_CHARGE_CYCLES.value
    PROJECT_SOC_DECREASE_KPI_ID = KPITypeEnum.BESS_PROJECT_DISCHARGE_CYCLES.value

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
        if not project.capacity_bess_energy_bol_dc:
            rte_dict[project_key] = None
            continue

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


async def get_project_rte_from_modules(
    *,
    project_ids: list[UUID],
    start: datetime.date,
    end: datetime.date,
) -> dict[UUID, float | None]:
    """Get the RTE using PCS-module charged/discharged energy KPI values.

    This function exists for backward compatibility with existing API/reporting
    code paths that historically used these KPI types.

    Args:
        project_ids: The project IDs to get the RTE for.
        start: The start date of the period.
        end: The end date of the period (exclusive).

    Returns:
        A dictionary of project IDs to RTE values.
    """
    pcs_module_energy_charged_kpi_id = KPITypeEnum.BESS_PCS_MODULE_ENERGY_CHARGED.value
    pcs_module_energy_discharged_kpi_id = (
        KPITypeEnum.BESS_PCS_MODULE_ENERGY_DISCHARGED.value
    )
    project_soc_increase_kpi_id = KPITypeEnum.BESS_PROJECT_CHARGE_CYCLES.value
    project_soc_decrease_kpi_id = KPITypeEnum.BESS_PROJECT_DISCHARGE_CYCLES.value

    threshold = 0.2

    projects = await crud_get_projects(project_ids=project_ids).get_async(
        output_type=OutputType.SQLALCHEMY
    )

    df = await crud_get_kpi_data(
        start=start,
        end=end,
        project_ids=[project.project_id for project in projects],
        kpi_type_ids=[
            pcs_module_energy_charged_kpi_id,
            pcs_module_energy_discharged_kpi_id,
            project_soc_increase_kpi_id,
            project_soc_decrease_kpi_id,
        ],
        include_device_data=False,
    ).get_async(output_type=OutputType.PANDAS)

    rte_dict: dict[UUID, float | None] = {}

    for project in projects:
        if project.name_short is None:
            continue

        project_key = project.project_id
        if not project.capacity_bess_energy_bol_dc:
            rte_dict[project_key] = None
            continue

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
                pcs_module_energy_charged_kpi_id,
                pcs_module_energy_discharged_kpi_id,
                project_soc_increase_kpi_id,
                project_soc_decrease_kpi_id,
            ]
        )

        energy_cols = [
            pcs_module_energy_charged_kpi_id,
            pcs_module_energy_discharged_kpi_id,
        ]
        pivot_df[energy_cols] = (
            pivot_df[energy_cols] / project.capacity_bess_energy_bol_dc
        )
        pivot_df = pivot_df.dropna()

        sum_df = pivot_df.sum(min_count=1)

        charge_total = sum_df[pcs_module_energy_charged_kpi_id]
        if charge_total < threshold:
            charge_total = np.nan
        discharge_total = sum_df[pcs_module_energy_discharged_kpi_id]
        if discharge_total < threshold:
            discharge_total = np.nan
        soc_increase_total = sum_df[project_soc_increase_kpi_id]
        if soc_increase_total < threshold:
            soc_increase_total = np.nan
        soc_decrease_total = sum_df[project_soc_decrease_kpi_id]
        if soc_decrease_total < threshold:
            soc_decrease_total = np.nan

        charge_efficiency = soc_increase_total / charge_total
        discharge_efficiency = discharge_total / soc_decrease_total
        rte = charge_efficiency * discharge_efficiency
        if rte > 1:
            rte = np.nan
        rte_dict[project_key] = rte

    return rte_dict


def calculate_rte(
    *,
    daily_energy_charged_series: pd.Series,
    daily_energy_discharged_series: pd.Series,
    energy_capacity: float,
) -> float:
    """
    A simple implementation of RTE
    There is no adjustment based on SOC increase or decrease.
    Only concurrent days are used and there must be at least 3 cycles

    Args:
        daily_energy_charged_series: Daily charged energy indexed by date.
        daily_energy_discharged_series: Daily discharged energy indexed by date.
        energy_capacity: Nameplate energy capacity used to compute cycle thresholds.
    """
    concat_df = pd.concat(
        [daily_energy_charged_series, daily_energy_discharged_series], axis=1
    )
    concat_df.columns = ["daily_energy_charged", "daily_energy_discharged"]
    # only use days where data is present for both days
    concat_df = concat_df.dropna()

    energy_charged_sum = concat_df["daily_energy_charged"].sum()
    energy_discharged_sum = concat_df["daily_energy_discharged"].sum()
    if energy_charged_sum < 3 * energy_capacity:
        return np.nan
    if energy_discharged_sum < 3 * energy_capacity:
        return np.nan
    rte = energy_discharged_sum / energy_charged_sum
    if rte > 1:
        return np.nan
    return cast(float, rte)


async def get_and_calculate_rte(
    *,
    project: models.Project,
    rte_type: Literal["POI", "POI_NO_AUX", "FEEDER", "DC"],
    start: datetime.date,
    end: datetime.date,
) -> float:
    if not project.capacity_bess_energy_bol_dc:
        return np.nan
    match rte_type:
        case "POI":
            charged_kpi_id = KPITypeEnum.BESS_PROJECT_ENERGY_CHARGED.value
            discharged_kpi_id = KPITypeEnum.PROJECT_ENERGY_DISCHARGED.value
        case "POI_NO_AUX":
            charged_kpi_id = KPITypeEnum.BESS_PROJECT_ENERGY_CHARGED_NO_AUX.value
            discharged_kpi_id = KPITypeEnum.PROJECT_ENERGY_DISCHARGED.value
        case "FEEDER":
            charged_kpi_id = KPITypeEnum.BESS_CIRCUIT_ENERGY_CHARGED.value
            discharged_kpi_id = KPITypeEnum.BESS_CIRCUIT_ENERGY_DISCHARGED.value
        case "DC":
            charged_kpi_id = KPITypeEnum.BESS_STRING_ENERGY_CHARGED.value
            discharged_kpi_id = KPITypeEnum.BESS_STRING_ENERGY_DISCHARGED.value
        case _:
            raise ValueError(f"Unsupported RTE type: {rte_type}")
    df = await crud_get_kpi_data(
        start=start,
        end=end,
        project_ids=[project.project_id],
        kpi_type_ids=[charged_kpi_id, discharged_kpi_id],
        include_device_data=False,
    ).get_async(
        schema=project.name_short,
        output_type=OutputType.PANDAS,
    )
    if df.empty:
        return np.nan
    df = df.set_index("date")
    daily_energy_charged_series = df.loc[
        df.kpi_type_id == charged_kpi_id, "project_data"
    ]
    daily_energy_discharged_series = df.loc[
        df.kpi_type_id == discharged_kpi_id, "project_data"
    ]
    energy_capacity = project.capacity_bess_energy_bol_dc
    return calculate_rte(
        daily_energy_charged_series=daily_energy_charged_series,
        daily_energy_discharged_series=daily_energy_discharged_series,
        energy_capacity=energy_capacity,
    )
