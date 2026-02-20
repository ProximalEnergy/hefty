import os

import plotly.graph_objects as go
import polars as pl
from dotenv import load_dotenv

# Database connection parameters
# Replace these with your actual connection details
from sqlalchemy import create_engine

# --- Config ---
project_name_short = "double_black_diamond"
expected_model_version = "0.10.0"
query_date = "2025-05-01"

# --- Environment ---
load_dotenv()
db_connection_string = os.getenv("DB_URI_PROD")
match db_connection_string:
    case None:
        raise ValueError("no connection string found in .env file")
    case _:
        pass

# Create SQLAlchemy engine
conn = create_engine(db_connection_string)

# Query for the first dataframe (data_expected)
query_expected = f"""
SELECT
    de.time,
    de.value,
    de.device_id,
    de.expected_metric_id
FROM
    {project_name_short}.data_expected de
JOIN
    {project_name_short}.devices d ON de.device_id = d.device_id
WHERE
    version = '{expected_model_version}'
    AND time >= '{query_date} 00:00:00'
    AND time < '{query_date} 23:55:00'
    AND d.device_type_id = 1
ORDER BY
    time
"""

query_raw = f"""
SELECT
    time,
    value_continuous
FROM
    double_black_diamond.data_raw
WHERE
    tag_id = 28716
    AND time >= '{query_date} 00:00:00'
    AND time < '{query_date} 23:00:00'
ORDER BY
    time
"""


# Fetch data
df_expected = pl.read_database(query=query_expected, connection=conn.connect())
# print(df_expected.filter(pl.col("value") < 1))

df_raw = pl.read_database(query=query_raw, connection=conn.connect())

# Process the raw data: resample to 5-minute averages
# First, ensure the time column is of datetime type
df_raw = df_raw.with_columns(pl.col("time").cast(pl.Datetime))

# Resample data into 5-minute bins
df_raw_resampled = df_raw.group_by_dynamic("time", every="5m", closed="left").agg(
    pl.col("value_continuous").mean().alias("value_continuous_avg")
)


# Create a dot and line chart with Plotly
fig = go.Figure()

# Add expected data as dots
unique_device_ids = df_expected["device_id"].unique().to_list()
for device_id in unique_device_ids:
    device_data = df_expected.filter(pl.col("device_id") == device_id)
    fig.add_trace(
        go.Scatter(
            x=device_data["time"].to_list(),
            y=device_data["value"].to_list(),
            mode="markers+lines",
            name=f"Expected Data ({device_id})",
            marker=dict(color="blue", size=8),
        )
    )

# Add raw data as line
fig.add_trace(
    go.Scatter(
        x=df_raw_resampled["time"].to_list(),
        y=df_raw_resampled["value_continuous_avg"].to_list(),
        mode="markers+lines",
        name="Raw Data (5min avg)",
        line=dict(color="red", width=2),
    ),
)

# Update layout
fig.update_layout(
    title=f"Database Data Comparison {query_date}",
    xaxis_title="Time",
    legend=dict(x=0.01, y=0.99),
    hovermode="x unified",
)

# Update y-axis labels
fig.update_yaxes(title_text="Expected Value")
fig.update_yaxes(
    title_text="Raw Value (5min Avg)",
)

# Show the figure
fig.show()

# print("Data extraction and visualization complete!")
