from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from p01_get_data.class_simulation_inputs import SimulationInputs
from p02_simulation.c_simulate_project import simulate_project

from _tests.snapshot_test_helpers import read_snapshot_inputs

SNAPSHOT_NAME = Path(__file__).stem
SIMULATION_START = "2026-04-15 11:55:00"
SIMULATION_END = "2026-04-15 12:05:00"
EXPECTED_NOON_TIME = pd.Timestamp(
    "2026-04-15 12:00:00",
    tz="America/Phoenix",
)
EXPECTED_NOON_POWER_W = 85_000_000.0
EXPECTED_MODULE_IDS = {23, 24}
EXPECTED_MODULE_MODELS = {"FS-6430A", "FS-6435A"}


def _read_inputs() -> SimulationInputs:
    return read_snapshot_inputs(
        snapshot_name=SNAPSHOT_NAME,
        simulation_start=SIMULATION_START,
        simulation_end=SIMULATION_END,
    )


def _build_poi_frame(*, simulation_inputs: SimulationInputs) -> pd.DataFrame:
    simulation = simulate_project(inputs=simulation_inputs)
    next(simulation)
    next(simulation)
    inverter = next(simulation)

    # This checkout expects "device_id" in the transformer step.
    inverter.device_ids = inverter.device_ids.rename("device_id")

    next(simulation)
    poi = next(simulation)

    poi_frame = pd.concat(
        [
            pd.to_datetime(poi.time).rename("time"),
            poi.power.rename("p_mp"),
        ],
        axis=1,
    )
    if poi_frame["time"].dt.tz is None:
        poi_frame["time"] = poi_frame["time"].dt.tz_localize("America/Phoenix")
    else:
        poi_frame["time"] = poi_frame["time"].dt.tz_convert("America/Phoenix")
    return poi_frame


def test_sun_pond_noon_poi_uses_pan_modules() -> None:
    simulation_inputs = _read_inputs()

    module_ids = set(simulation_inputs.system.module_equipment_id.unique())
    assert module_ids == EXPECTED_MODULE_IDS

    module_frame = pd.concat(
        [
            simulation_inputs.modules.module_equipment_id,
            simulation_inputs.modules.model,
            simulation_inputs.modules.data_source,
        ],
        axis=1,
    ).drop_duplicates(subset=["module_equipment_id"])

    assert set(module_frame["model"]) == EXPECTED_MODULE_MODELS
    assert set(module_frame["data_source"]) == {"pan"}

    poi_frame = _build_poi_frame(simulation_inputs=simulation_inputs)
    poi_frame["delta_s"] = (
        (poi_frame["time"] - EXPECTED_NOON_TIME).abs().dt.total_seconds()
    )
    nearest_noon = poi_frame.sort_values("delta_s").iloc[0]

    assert nearest_noon["delta_s"] == 0.0
    assert float(nearest_noon["p_mp"]) == pytest.approx(
        EXPECTED_NOON_POWER_W,
        abs=1.0,
    )
