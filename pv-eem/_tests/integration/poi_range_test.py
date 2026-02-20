import asyncio
import os

import pandas as pd
import plotly.graph_objects as go
from src.main import get_expected_energy
from src.p00_parse_input.simulation_temporal_mode import SimulationTemporalMode
from src.p02_simulation.p3_epoai.s01_direct_shade import ModelCircumsolar
from src.p02_simulation.p3_epoai.s05_soiling import ModelSoiling


def test_simulation():
    # --- Constants ---
    os.environ["ENVIRONMENT"] = "DEV"
    OUTPUT_FILE_NAME = "../_artifacts/_interconnection.pq"

    # --- File Load ---

    # --- Main Simulation ---
    _results: dict = asyncio.run(
        get_expected_energy(
            # ARGS
            project_name_short="double_black_diamond",
            simulation_temporal_mode=SimulationTemporalMode.WINDOW,
            simulation_start="2024-10-20 00:00:00",
            simulation_end="2024-10-20 23:59:59",
            # KWARGS
            sun_position_offset=0,
            soiling=ModelSoiling.NONE,
            circumsolar=ModelCircumsolar.DIFFUSE,
        )
    )
    # Get the script's absolute directory
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct the output path
    output_file_path = os.path.normpath(os.path.join(script_dir, OUTPUT_FILE_NAME))

    poi = pd.read_parquet(output_file_path)

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
