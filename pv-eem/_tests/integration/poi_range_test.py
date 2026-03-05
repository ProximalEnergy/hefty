import asyncio
import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from p03_export.s00_simulation_level import SimulationLevel
from src.main import get_expected_energy
from src.p00_parse_input.simulation_temporal_mode import SimulationTemporalMode
from src.p02_simulation.p3_epoai.s01_direct_shade import ModelCircumsolar
from src.p02_simulation.p3_epoai.s05_soiling import ModelSoiling

from _tests.snapshot_test_helpers import (
    build_output_file_path,
    install_snapshot_inputs_loader_patch,
    install_unique_export_patch,
    remove_output_file_if_exists,
)

SNAPSHOT_NAME = Path(__file__).stem
TEST_NAME = "test_simulation"
OUTPUT_NAMESPACE = f"{SNAPSHOT_NAME}_{TEST_NAME}"
PROJECT_NAME_SHORT = "double_black_diamond"
SIMULATION_START = "2024-10-20 00:00:00"
SIMULATION_END = "2024-10-20 23:59:59"
OUTPUT_FILE_PATH = build_output_file_path(
    test_namespace=OUTPUT_NAMESPACE,
    project_name_short=PROJECT_NAME_SHORT,
    simulation_start=SIMULATION_START,
    simulation_level=SimulationLevel.INTERCONNECTION,
)


def test_simulation(monkeypatch):
    # --- Constants ---
    os.environ["ENVIRONMENT"] = "DEV"

    # --- File Load ---
    install_snapshot_inputs_loader_patch(
        monkeypatch=monkeypatch,
        snapshot_name=SNAPSHOT_NAME,
    )
    install_unique_export_patch(
        monkeypatch=monkeypatch,
        test_namespace=OUTPUT_NAMESPACE,
    )
    remove_output_file_if_exists(output_file_path=OUTPUT_FILE_PATH)

    # --- Main Simulation ---
    results: dict = asyncio.run(
        get_expected_energy(
            # ARGS
            project_name_short=PROJECT_NAME_SHORT,
            simulation_temporal_mode=SimulationTemporalMode.WINDOW,
            simulation_start=SIMULATION_START,
            simulation_end=SIMULATION_END,
            # KWARGS
            sun_position_offset=0,
            soiling=ModelSoiling.NONE,
            circumsolar=ModelCircumsolar.DIFFUSE,
        )
    )
    assert results.get("status_code") == 200, results

    poi = pd.read_parquet(OUTPUT_FILE_PATH)

    # --- Test ---
    try:
        assert poi["p_mp"].max() <= 592_800_000, (
            f"Maximum p_mp value {poi['p_mp'].max()} exceeds 592.8 MW POI limit"
        )

        assert poi["p_mp"].min() >= 0, (
            f"Minimum p_mp value {poi['p_mp'].min()} is less than 0"
        )
    except AssertionError:
        # Create figure
        fig = go.Figure()

        # Add bar trace
        fig.add_trace(
            go.Scatter(
                x=poi["time"],
                y=poi["p_mp"],
                name="p_mp at poi",
                mode="lines+markers",
            )
        )

        # Update layout
        fig.update_layout(
            title="POI Range Test",
            xaxis_title="time",
            yaxis_title="power (W)",
        )

        # Show figure
        fig.show()
        raise
