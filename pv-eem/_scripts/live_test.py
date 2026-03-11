#!/usr/bin/env python3
"""Run a live pv-eem sanity check against sun_pond."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from pprint import pformat

from dotenv import load_dotenv

PVEEM_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PVEEM_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from main import get_expected_energy
from p00_parse_input.simulation_temporal_mode import SimulationTemporalMode
from p01_get_data.source_proximal.s02_get_database_engine import get_db_engine
from p01_get_data.source_proximal.s03_get_project import Project
from p01_get_data.source_proximal.s04_get_met_data import get_met_data

PROJECT_NAME_SHORT = "sun_pond"
SIMULATION_START = "2026-03-10 12:00:00"
SIMULATION_END = "2026-03-10 12:05:00"
SIMULATION_CONFIG = {
    "single_diode_model": "DESOTO",
    "degradation": "warranted",
    "use_poa_only": False,
}


def _load_environment() -> None:
    load_dotenv(PVEEM_ROOT / ".env")


def _get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set in pv-eem/.env")
    return database_url


async def _get_project() -> Project:
    return await Project.create(
        project_name_short=PROJECT_NAME_SHORT,
    )


async def _get_live_met_data_row_count(
    *,
    database_url: str,
) -> int:
    engine = get_db_engine(database_url=database_url)
    project = await Project.create(
        project_name_short=PROJECT_NAME_SHORT,
    )
    met_data = await get_met_data(
        time_zone=project.time_zone,
        project_name_short=PROJECT_NAME_SHORT,
        project_data_table_name=project.data_table,
        simulation_temporal_mode=SimulationTemporalMode.WINDOW.value,
        simulation_start=SIMULATION_START,
        simulation_end=SIMULATION_END,
        engine=engine,
        ENVIRONMENT=os.environ.get("ENVIRONMENT", ""),
    )
    if met_data.is_empty():
        raise RuntimeError(
            "Live test failed: no met data returned for "
            f"{PROJECT_NAME_SHORT} at {SIMULATION_START} {project.time_zone}"
        )
    print("Met data sample:")
    print(met_data.head(5))
    return met_data.height


async def _run_live_test() -> dict[str, object]:
    return await get_expected_energy(
        project_name_short=PROJECT_NAME_SHORT,
        simulation_temporal_mode=SimulationTemporalMode.WINDOW,
        simulation_start=SIMULATION_START,
        simulation_end=SIMULATION_END,
        **SIMULATION_CONFIG,
    )


async def _async_main() -> int:
    database_url = _get_database_url()
    project = await _get_project()
    print(
        "Running pv-eem live test for "
        f"{PROJECT_NAME_SHORT} in {project.time_zone}"
    )
    print(f"Window: {SIMULATION_START} to {SIMULATION_END}")
    print(f"Config: {pformat(SIMULATION_CONFIG)}")

    met_data_rows = await _get_live_met_data_row_count(database_url=database_url)
    print(f"Met data rows: {met_data_rows}")

    result = await _run_live_test()
    print(f"Simulation result: {pformat(result)}")

    if result.get("status_code") != 200:
        raise RuntimeError("Live test failed: simulation did not return status 200")

    return 0


def main() -> int:
    _load_environment()
    return asyncio.run(_async_main())


if __name__ == "__main__":
    raise SystemExit(main())
