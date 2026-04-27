import logging

import plotly.graph_objects as go
import polars as pl
from plotly.colors import qualitative

logger = logging.getLogger(__name__)


def plot_modeled_vs_measured(
    *,
    modeled: pl.DataFrame,
    measured: pl.DataFrame,
) -> None:
    """Run plot."""
    color_scale = qualitative.Dark24

    # --- Pivot ---
    measured = measured.pivot(
        on="combiner_device_id",
        values="value_continuous",
        index="time",
    )

    logger.info("%s", measured.columns[1:])
    modeled = modeled.filter(
        pl.col("combiner_device_id").cast(str).is_in(measured.columns[1:])
    )
    modeled = modeled.with_columns((pl.col("p_mp") / 1000).alias("p_mp"))
    logger.info("%s", modeled)
    modeled = modeled.pivot(
        on="combiner_device_id",
        values="p_mp",
        index="time",
    )
    modeled.write_csv("combiners_modeled.csv")

    # Create the plot
    fig = go.Figure()
    logger.info("%s", modeled.head())
    logger.info("%s", measured.head())

    for i, col in enumerate(measured.columns[2:]):
        color = color_scale[i % len(color_scale)]
        fig.add_trace(
            go.Scatter(
                x=modeled["time"],
                y=modeled[col],
                mode="markers",
                name=f"modeled_{col}",
                opacity=0.5,
                marker=dict(color=color),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=measured["time"],
                y=measured[col],
                mode="markers",
                name=col,
                opacity=0.75,
                marker=dict(color=color),
            )
        )

    # Customize the plot
    fig.update_layout(
        title="Time Series Data",
        xaxis_title="Time",
        yaxis_title="tracker_rotations",
        showlegend=True,
        xaxis=dict(
            tickangle=45,
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(128,128,128,0.2)",
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(128,128,128,0.2)",
        ),
    )

    fig.show()
