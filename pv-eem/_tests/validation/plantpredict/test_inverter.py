import asyncio
import logging
import os

import pandas as pd
import plotly.graph_objects as go
from p02_simulation.p4_dc_iv.s02_single_diode_params import ModelSingleDiode
from plotly.subplots import make_subplots
from src.main import get_expected_energy
from src.p00_parse_input.simulation_temporal_mode import SimulationTemporalMode
from src.p02_simulation.p3_epoai.s01_direct_shade import ModelCircumsolar
from src.p02_simulation.p3_epoai.s05_soiling import ModelSoiling
from src.p02_simulation.p4_dc_iv.s04_iv_2_warranted_degradation import ModelDegradation

logger = logging.getLogger(__name__)


def test_inverter():
    """Checks to see if a single day for a single combiner gives similar values
    PlantPredict simulation has:
        - 40% GCR
        - 112 strings in parallel
    """
    # --- Dataframe Config ---
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)
    pd.set_option("display.max_rows", None)

    # --- Constants ---
    OUTPUT_FILE_NAME = "../../_artifacts/_inverter.pq"
    PLANTPREDICT_FILE_NAME = "_plantpredict_inverter.csv"
    TIMEZONE = "America/Chicago"

    # --- File Load ---
    os.environ["ENVIRONMENT"] = "DEV"

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
            degradation=ModelDegradation.NONE,
            circumsolar=ModelCircumsolar.DIFFUSE,
            single_diode_model=ModelSingleDiode.DESOTO,
        )
    )
    # Get the script's absolute directory
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Construct the output path
    output_file_path = os.path.normpath(os.path.join(script_dir, OUTPUT_FILE_NAME))

    simulation_outputs = pd.read_parquet(output_file_path)
    simulation_outputs = simulation_outputs.loc[simulation_outputs["device_id"] == 206]

    simulation_outputs = simulation_outputs[["time", "p_mp", "tier"]]
    simulation_outputs = simulation_outputs.rename(  # type: ignore
        columns={"p_mp": "proximal_simulated_power"}
    )  #  type: ignore

    # Load PlantPredict outputs
    pp_file_path = os.path.join(os.path.dirname(__file__), PLANTPREDICT_FILE_NAME)
    pp_outputs = pd.read_csv(
        pp_file_path,
        header=2,
        encoding="UTF-16-le",
        usecols=[
            "Timestamp (yyyy-MM-dd HH:mm:ss)",
            "AC Power (W)",
        ],  # type: ignore
    )
    pp_outputs = pp_outputs.rename(
        columns={
            "AC Power (W)": "pp_simulated_power",
        }
    )

    # Convert timestamp column to datetime
    pp_outputs["time"] = pd.to_datetime(
        pp_outputs["Timestamp (yyyy-MM-dd HH:mm:ss)"]
    ).dt.tz_localize(TIMEZONE)
    pp_outputs["time"] = pp_outputs["time"] + pd.Timedelta(hours=1)
    pp_outputs = pp_outputs.drop("Timestamp (yyyy-MM-dd HH:mm:ss)", axis=1)

    df = pd.merge(left=simulation_outputs, right=pp_outputs, on=["time"], how="inner")

    # Calculate the percentage difference
    df["delta_percent"] = (
        (df["pp_simulated_power"] - df["proximal_simulated_power"])
        / df["proximal_simulated_power"]
        * 100
    )

    # Filter data for hours 9-16
    df_filtered = df[(df["time"].dt.hour >= 10) & (df["time"].dt.hour <= 15)]

    # Calculate mean absolute percentage difference
    max_delta = abs(df_filtered["delta_percent"]).max()
    logger.info("%s", max_delta)

    # Assert mean difference is within tolerance
    try:
        assert max_delta <= 1.6
    except AssertionError:
        # Create figure with secondary y-axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Add traces for each tier of proximal_simulated_power
        for tier in df["tier"].unique():
            tier_data = df[df["tier"] == tier]

            fig.add_trace(
                go.Scatter(
                    x=tier_data["time"],
                    y=tier_data["proximal_simulated_power"],
                    name=f"proximal_simulated_power (tier {tier})",
                    mode="markers"
                    if tier == 3
                    else "lines+markers",  # Only markers for tier 3, lines+markers for
                    # others
                    line=dict(color="blue", width=2),
                    marker=dict(
                        size=6
                    ),  # Optional: specify marker size for consistency
                ),
                secondary_y=False,
            )

        fig.add_trace(
            go.Scatter(
                x=df["time"],
                y=df["pp_simulated_power"],
                name="pp_simulated_power",
                line=dict(color="red"),
            ),
            secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(
                x=df["time"],
                y=df["delta_percent"],
                name="Delta (%)",
                line=dict(color="green"),
            ),
            secondary_y=True,
        )

        # Update layout
        fig.update_layout(
            title="Inverter Comparison",
            xaxis=dict(title="Time", tickangle=45),
            legend=dict(x=1.1, y=1),
            showlegend=True,
            width=1200,
            height=700,
        )

        # Update yaxis properties
        fig.update_yaxes(title_text="Power (W)", secondary_y=False)
        fig.update_yaxes(title_text="Delta (%)", secondary_y=True)

        # Show plot
        fig.show()
        raise
