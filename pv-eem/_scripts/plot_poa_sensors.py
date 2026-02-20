"""
Script to plot POA sensors for north_star project between two given dates using Plotly.

Usage:
    Edit the dates in the if __name__ == "__main__" section, then run:
    uv run python _scripts/plot_poa_sensors.py
"""

import os
from datetime import datetime

import plotly.graph_objects as go
import polars as pl
import pytz
from dotenv import load_dotenv
from sqlalchemy import create_engine


def plot_poa_sensors(
    *,
    start_date: str,
    end_date: str,
    project_name_short: str = "north_star",
    time_zone: str = "America/New_York",
):
    """
    Plot POA sensors for a given project between two dates.

    Args:
        start_date: Start date in format "YYYY-MM-DD HH:MM:SS" (local time)
        end_date: End date in format "YYYY-MM-DD HH:MM:SS" (local time)
        project_name_short: Short name of the project (default: north_star)
        time_zone: Time zone of the project (default: America/New_York)
    """
    # --- Get database connection ---
    load_dotenv()
    db_connection_string = os.getenv("DB_URI_PROD")
    if db_connection_string is None:
        raise ValueError("no connection string found in .env file")

    engine = create_engine(db_connection_string)

    # --- Convert times to UTC ---
    start_time_naive = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
    end_time_naive = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")

    tz = pytz.timezone(time_zone)
    start_time_aware = tz.localize(start_time_naive)
    end_time_aware = tz.localize(end_time_naive)

    start_time_utc = start_time_aware.astimezone(pytz.utc)
    end_time_utc = end_time_aware.astimezone(pytz.utc)

    start_str = start_time_utc.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end_time_utc.strftime("%Y-%m-%d %H:%M:%S")

    print(f"Querying database for {project_name_short}...")
    print(f"Date range (UTC): {start_str} to {end_str}")

    # --- Get column names for POA sensors ---
    column_query = f"""
        SELECT DISTINCT ON (sensor_type.name_short)
            tags.tag_id as tag_id,
            sensor_type.name_short as sensor_name,
            pg_data_types.name_short as data_column_name,
            sensor_type.unit as unit
        FROM {project_name_short}.tags as tags
        LEFT JOIN operational.pg_data_types as pg_data_types
            ON tags.pg_data_type_id = pg_data_types.pg_data_type_id
        LEFT JOIN operational.sensor_types AS sensor_type
            ON tags.sensor_type_id = sensor_type.sensor_type_id
        WHERE sensor_type.name_short in (
            'met_station_poa',
            'met_station_poa_tilt'
        )
    """

    with engine.connect() as conn:
        column_info = pl.read_database(query=column_query, connection=conn)

    if column_info.height == 0:
        print("No POA sensors found in tags")
        return

    print(f"\nFound {column_info.height} POA sensor types")
    print(column_info)

    # Check what columns exist in data_timeseries
    check_columns_query = f"""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = '{project_name_short}'
    AND table_name = 'data_timeseries'
    ORDER BY ordinal_position
    """
    with engine.connect() as conn:
        columns_df = pl.read_database(query=check_columns_query, connection=conn)
        print("\nColumns in data_timeseries table:")
        print(columns_df)

    # --- Build and execute queries for each sensor type ---
    all_data_frames = []

    for row in column_info.iter_rows(named=True):
        sensor_name = row["sensor_name"]
        column_name = row["data_column_name"]
        unit = row["unit"]

        # Map pg_data_type name to actual column name
        if column_name == "real":
            column_name = "value_real"
        elif column_name == "double":
            column_name = "value_double"
        elif column_name == "integer":
            column_name = "value_integer"
        elif column_name == "bigint":
            column_name = "value_bigint"
        elif column_name == "boolean":
            column_name = "value_boolean"
        elif column_name == "text":
            column_name = "value_text"

        query = f"""
        SELECT
            time_bucket('5 minutes', time) as time,
            AVG(data.{column_name}) as value,
            STDDEV(data.{column_name}) as std_dev,
            '{sensor_name}' AS sensor_name,
            '{unit}' as unit,
            devices.name_short AS met_name
        FROM {project_name_short}.data_timeseries AS data
        LEFT JOIN {project_name_short}.tags AS tags
            ON data.tag_id = tags.tag_id
        LEFT JOIN {project_name_short}.devices AS devices
            ON tags.device_id = devices.device_id
        LEFT JOIN operational.sensor_types AS sensor_type
            ON tags.sensor_type_id = sensor_type.sensor_type_id
        WHERE time >= TIMESTAMP '{start_str}'
        AND time <= TIMESTAMP '{end_str}'
        AND data.{column_name} IS NOT NULL
        AND sensor_type.name_short = '{sensor_name}'
        GROUP BY
            time_bucket('5 minutes', time),
            devices.name_short
        ORDER BY
            time,
            devices.name_short
        """

        with engine.connect() as conn:
            sensor_data = pl.read_database(query=query, connection=conn)
            if sensor_data.height > 0:
                all_data_frames.append(sensor_data)

    if len(all_data_frames) == 0:
        print("No POA data found for the specified date range.")
        return

    # Combine all data
    poa_data = pl.concat(all_data_frames)

    if poa_data.height == 0:
        print("No POA data found for the specified date range.")
        return

    print(f"Found {poa_data.height} records")

    # --- Create plot with subplots ---
    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("POA Sensor Values", "Z-Score from Median"),
        vertical_spacing=0.12,
        row_heights=[0.6, 0.4],
    )

    # Calculate median and std dev across all sensors at each time point
    stats_by_time = (
        poa_data.group_by("time")
        .agg(
            [
                pl.col("value").std().alias("std_dev"),
                pl.col("value").median().alias("median_value"),
            ]
        )
        .sort("time")
    )

    # Join stats back to original data
    poa_data_with_stats = poa_data.join(stats_by_time, on="time", how="left")

    # Calculate z-score (number of std devs from median) as absolute value, capped at 50
    poa_data_with_stats = poa_data_with_stats.with_columns(
        ((pl.col("value") - pl.col("median_value")) / pl.col("std_dev")).abs().clip(upper_bound=50).alias("z_score")
    )

    # Get unique combinations of met_name and sensor_name
    groups = poa_data_with_stats.select(["met_name", "sensor_name"]).unique().sort("met_name")

    # Color palette for consistent colors
    import plotly.express as px
    colors = px.colors.qualitative.Plotly

    for idx, row in enumerate(groups.iter_rows(named=True)):
        met_name = row["met_name"]
        sensor_name = row["sensor_name"]
        color = colors[idx % len(colors)]

        # Filter data for this combination
        filtered_data = poa_data_with_stats.filter(
            (pl.col("met_name") == met_name) & (pl.col("sensor_name") == sensor_name)
        )

        # Calculate average z-score for this sensor
        avg_z_score = filtered_data["z_score"].mean()

        # Add trace for sensor values (top plot)
        fig.add_trace(
            go.Scatter(
                x=filtered_data["time"].to_list(),
                y=filtered_data["value"].to_list(),
                mode="lines",
                name=f"{met_name} - {sensor_name} (avg {avg_z_score:.2f}σ)",
                line=dict(width=1, color=color),
                legendgroup=f"{met_name}_{sensor_name}",
            ),
            row=1, col=1
        )

        # Add trace for z-scores (bottom plot)
        fig.add_trace(
            go.Scatter(
                x=filtered_data["time"].to_list(),
                y=filtered_data["z_score"].to_list(),
                mode="lines",
                name=f"{met_name} - {sensor_name}",
                line=dict(width=1, color=color),
                legendgroup=f"{met_name}_{sensor_name}",
                showlegend=False,
            ),
            row=2, col=1
        )

    # Calculate std dev as percentage of median (reuse stats_by_time)
    std_by_time = stats_by_time.with_columns(
        ((pl.col("std_dev") / pl.col("median_value")) * 100).alias("std_dev_pct")
    )

    # Add standard deviation percentage trace to top plot
    fig.add_trace(
        go.Scatter(
            x=std_by_time["time"].to_list(),
            y=std_by_time["std_dev_pct"].to_list(),
            mode="lines",
            name="Std Dev % of Median",
            line=dict(width=2, dash="dash", color="red"),
            yaxis="y3",
        ),
        row=1, col=1
    )

    # Get unit from the first record
    unit = poa_data["unit"][0]

    # Update layout
    fig.update_layout(
        title=f"POA Sensors - {project_name_short}<br>{start_date} to {end_date}",
        hovermode="x unified",
        height=800,
        template="plotly_white",
    )

    # Update both subplots to have unified hover on x
    fig.update_xaxes(matches='x')

    # Sync hover between subplots
    for i in fig.data:
        i.xaxis = 'x'

    # Update y-axis labels
    fig.update_yaxes(title_text=f"Irradiance ({unit})", row=1, col=1)
    fig.update_yaxes(title_text="Z-Score (|σ| from median, capped at 50)", row=2, col=1)
    fig.update_xaxes(title_text="Time", row=2, col=1)

    # Add secondary y-axis for std dev percentage on top plot
    fig.update_layout(
        yaxis3=dict(
            title="Std Dev (% of Median)",
            overlaying="y",
            side="right",
            anchor="x",
        )
    )

    # Show plot
    print("Opening plot in browser...")
    fig.show()


if __name__ == "__main__":
    # --- Edit these dates as needed ---
    start_date = "2025-09-15 00:00:00"
    end_date = "2025-09-16 23:59:59"
    project_name_short = "north_star"
    time_zone = "America/Chicago"

    plot_poa_sensors(
        start_date=start_date,
        end_date=end_date,
        project_name_short=project_name_short,
        time_zone=time_zone,
    )
