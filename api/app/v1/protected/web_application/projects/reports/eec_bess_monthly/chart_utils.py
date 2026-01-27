"""Chart generation utilities for report generation.

This module contains reusable functions for creating Plotly charts
used in PDF reports.
"""

from typing import cast

import numpy as np  # type: ignore
import pandas as pd
import plotly.graph_objects as go  # type: ignore
from numpy.typing import NDArray  # type: ignore

# ---------------------------------------------------------------------------
# Chart Configuration
# ---------------------------------------------------------------------------

DEFAULT_CHART_HEIGHT = 600
DEFAULT_CHART_WIDTH = 1200
DEFAULT_COLORS = ["blue", "orange", "green", "purple", "red", "cyan"]


# ---------------------------------------------------------------------------
# Chart Generation Functions
# ---------------------------------------------------------------------------


type FloatArray = NDArray[np.float64]


def create_stacked_bar_chart(
    *,
    df: pd.DataFrame,
    bar_columns: list[str],
    line_column: str | None = None,
    title: str = "",
    xaxis_title: str = "",
    yaxis_title: str = "",
    yaxis_format: str = "$,.0f",
    xaxis_tickformat: str = "%b %d, %Y",
    height: int = DEFAULT_CHART_HEIGHT,
    width: int = DEFAULT_CHART_WIDTH,
    colors: list[str] | None = None,
) -> go.Figure:
    """Create a stacked bar chart with optional line overlay.

    Handles positive and negative values separately for proper stacking.

    Args:
        df: DataFrame with index as x-axis and columns as series.
        bar_columns: List of column names to display as stacked bars.
        line_column: Optional column name to overlay as a line.
        title: Chart title.
        xaxis_title: X-axis title.
        yaxis_title: Y-axis title.
        yaxis_format: Format string for y-axis ticks (e.g., "$,.0f").
        xaxis_tickformat: Format string for x-axis date ticks.
        height: Chart height in pixels.
        width: Chart width in pixels.
        colors: Optional list of colors for bars (cycles if needed).

    Returns:
        Plotly Figure object.
    """
    if colors is None:
        colors = DEFAULT_COLORS

    fig = go.Figure()

    x = df.index.values
    bottom_positive = cast(FloatArray, np.zeros(len(x), dtype=float))
    bottom_negative = cast(FloatArray, np.zeros(len(x), dtype=float))

    # Add stacked bars for each column
    for i, col in enumerate(bar_columns):
        if col not in df.columns:
            continue
        numeric_series = pd.to_numeric(df[col], errors="coerce")
        values = cast(
            FloatArray,
            numeric_series.to_numpy(dtype=float, na_value=np.nan),
        )
        positive = cast(
            FloatArray,
            np.where(values >= 0.0, values, 0.0),
        )
        negative = cast(
            FloatArray,
            np.where(values < 0.0, values, 0.0),
        )

        color = colors[i % len(colors)]

        # Positive values
        fig.add_trace(
            go.Bar(
                x=x,
                y=positive,
                base=bottom_positive,
                name=col,
                marker_color=color,
            )
        )

        # Negative values (same color, no legend)
        fig.add_trace(
            go.Bar(
                x=x,
                y=negative,
                base=bottom_negative,
                marker_color=color,
                showlegend=False,
            )
        )

        # Update bottom positions for next series
        bottom_positive += positive
        bottom_negative += negative

    # Add line trace if specified
    if line_column and line_column in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[line_column],
                mode="lines+markers",
                name=line_column,
                line=dict(color="black", width=2),
                marker=dict(size=8),
            )
        )

    # Update layout
    fig.update_layout(
        title=title,
        barmode="stack",
        xaxis=dict(
            title=xaxis_title,
            showgrid=False,
            showline=False,
            tickangle=-90,
            tickformat=xaxis_tickformat,
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            title=yaxis_title,
            showgrid=False,
            showline=False,
            tickformat=yaxis_format,
            zeroline=True,
            zerolinecolor="black",
            zerolinewidth=0.8,
        ),
        plot_bgcolor="white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        height=height,
        width=width,
    )

    return fig


def create_bar_chart(
    *,
    x: list | pd.Series | pd.Index,
    y: list | pd.Series,
    title: str = "",
    xaxis_title: str = "",
    yaxis_title: str = "",
    yaxis_format: str = ".0%",
    yaxis_range: tuple[float, float] | None = None,
    height: int = DEFAULT_CHART_HEIGHT,
    width: int = DEFAULT_CHART_WIDTH,
    show_legend: bool = False,
) -> go.Figure:
    """Create a simple bar chart.

    Args:
        x: X-axis values.
        y: Y-axis values.
        title: Chart title.
        xaxis_title: X-axis title.
        yaxis_title: Y-axis title.
        yaxis_format: Format string for y-axis ticks.
        yaxis_range: Optional tuple (min, max) for y-axis range.
        height: Chart height in pixels.
        width: Chart width in pixels.
        show_legend: Whether to show legend.

    Returns:
        Plotly Figure object.
    """
    fig = go.Figure(
        data=[
            go.Bar(
                x=x,
                y=y,
            )
        ]
    )

    yaxis_config = dict(
        title=yaxis_title,
        showgrid=True,
        showline=False,
        tickformat=yaxis_format,
        zeroline=True,
        zerolinecolor="black",
        zerolinewidth=0.8,
    )
    if yaxis_range:
        yaxis_config["range"] = yaxis_range

    fig.update_layout(
        title=title,
        xaxis=dict(
            title=xaxis_title,
            showgrid=False,
            showline=False,
        ),
        yaxis=yaxis_config,
        plot_bgcolor="white",
        legend=None if not show_legend else dict(),
        height=height,
        width=width,
    )

    return fig


def create_waterfall_chart(
    *,
    total_capacity: float,
    losses: dict[str, float],
    title: str = "",
    xaxis_title: str = "",
    yaxis_title: str = "",
    yaxis_format: str = ",.2f",
    height: int = DEFAULT_CHART_HEIGHT,
    width: int = DEFAULT_CHART_WIDTH,
) -> go.Figure:
    """Create a waterfall chart showing capacity losses by failure mode.

    Args:
        total_capacity: Starting available capacity (MWh).
        losses: Mapping of failure mode names to loss values (negative numbers
            indicate reductions.
        title: Chart title.
        xaxis_title: X-axis label.
        yaxis_title: Y-axis label.
        yaxis_format: Format string for y-axis ticks.
        height: Chart height.
        width: Chart width.

    Returns:
        Plotly Figure object representing the waterfall chart.
    """
    losses = losses or {}
    ordered_losses = {k: float(v) for k, v in losses.items()}
    steps = list(ordered_losses.items())

    total_capacity_value = float(total_capacity)
    remaining_capacity = total_capacity_value + sum(ordered_losses.values())

    x = ["Available Capacity", *[name for name, _ in steps], "Remaining Capacity"]
    y = [total_capacity_value, *[value for _, value in steps], remaining_capacity]
    measures = ["absolute", *["relative"] * len(steps), "total"]

    fig = go.Figure(
        go.Waterfall(
            x=x,
            y=y,
            measure=measures,
            text=[f"{value:,.2f} MWh" for value in y],
            connector={"line": {"color": "rgba(0,0,0,0.2)"}},
        )
    )

    fig.update_layout(
        title=title,
        xaxis=dict(title=xaxis_title),
        yaxis=dict(title=yaxis_title, tickformat=yaxis_format),
        showlegend=False,
        plot_bgcolor="white",
        height=height,
        width=width,
    )

    return fig
