from datetime import UTC, datetime
from io import BytesIO
from typing import Annotated

import pandas as pd
import polars as pl
from core.db_query import DbQuery
from fastapi import Depends, HTTPException
from fastapi.responses import StreamingResponse
from natsort import natsort_keygen
from sqlalchemy import select

from app import dependencies
from app.v1.protected.web_application.projects.reports.reports import router
from core import models

STALE_THRESHOLD_SECONDS = 3_600  # 1 hour


@router.get("/scada-telemetry-last-reported")
async def get_scada_telemetry_last_reported(
    project: Annotated[models.Project, Depends(dependencies.get_project_api)],
):
    """Generate Excel report with tag reporting status.

    Returns Excel binary with:
    - Summary sheet: aggregates (total, reporting, never reported, ghost count)
    - Data sheet: all tags with last reported time, status, ghost indicator

    Args:
        project: The project model.
    """

    # Query tags with LEFT JOIN to data_timeseries_last
    stmt = select(
        models.Tag.tag_id,
        models.Tag.name_scada,
        models.Tag.device_id,
        models.DataTimeseriesLast.time,
    ).outerjoin(
        models.DataTimeseriesLast,
        models.Tag.tag_id == models.DataTimeseriesLast.tag_id,
    )

    # Execute query and get polars DataFrame
    df: pl.DataFrame = await DbQuery(query=stmt, use_scalars=False).get_async(
        schema=project.name_short
    )
    if df.is_empty():
        raise HTTPException(
            status_code=404,
            detail="No tags found for this project.",
        )

    # Current time for staleness calculation (UTC) and report metadata (UTC)
    now_utc = datetime.now(UTC)

    # Add derived columns
    df = df.with_columns(
        # Is Ghost: device_id == 0
        pl.when(pl.col("device_id") == 0)
        .then(pl.lit(True))
        .otherwise(pl.lit(False))
        .alias("Ghost"),
        # Status: Never Reported, Fresh, or Stale
        pl.when(pl.col("time").is_null())
        .then(pl.lit("Never"))
        .otherwise(
            pl.when(
                (pl.lit(now_utc) - pl.col("time")).dt.total_seconds()
                > STALE_THRESHOLD_SECONDS
            )
            .then(pl.lit("Stale"))
            .otherwise(pl.lit("Fresh"))
        )
        .alias("Status"),
    )

    # Calculate summary statistics
    summary_counts = df.select(
        total_tags=pl.len(),
        tags_never_reported=pl.col("Status").eq("Never").sum(),
        ghost_tags=pl.col("Ghost").sum(),
        fresh_tags=pl.col("Status").eq("Fresh").sum(),
        stale_tags=pl.col("Status").eq("Stale").sum(),
    ).row(0)
    (
        total_tags,
        tags_never_reported,
        ghost_tags,
        fresh_tags,
        stale_tags,
    ) = summary_counts
    tags_reporting = total_tags - tags_never_reported

    # Create summary DataFrame
    summary_df = pl.DataFrame(
        {
            "Metric": [
                "Report Generated",
                "Project Name",
                "Total Tags",
                "Tags Reporting",
                "Tags Never Reporting",
                "Ghost Tags",
                "Fresh Tags",
                "Stale Tags",
            ],
            "Value": [
                now_utc.isoformat(),
                project.name_long,
                str(total_tags),
                str(tags_reporting),
                str(tags_never_reported),
                str(ghost_tags),
                str(fresh_tags),
                str(stale_tags),
            ],
        }
    )

    # Select and rename columns for data sheet
    data_df = df.select(
        [
            pl.col("name_scada").alias("Tag Name"),
            pl.col("Ghost"),
            pl.col("time").alias("Last Reported"),
            pl.col("Status"),
        ]
    )

    # Generate Excel file using polars
    excel_buffer = BytesIO()

    # Convert to pandas for Excel writing (xlsxwriter via pandas)
    summary_pd = summary_df.to_pandas()
    data_pd = data_df.to_pandas()
    natsort_key = natsort_keygen()
    data_pd = data_pd.sort_values(
        by="Tag Name",
        key=lambda series: series.fillna("").astype(str).map(natsort_key),
        kind="mergesort",
    )
    last_reported = pd.to_datetime(data_pd["Last Reported"], utc=True)
    last_reported = last_reported.dt.tz_convert(project.time_zone)
    data_pd["Last Reported"] = last_reported.dt.strftime("%Y-%m-%dT%H:%M:%S%z")

    with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
        summary_pd.to_excel(writer, sheet_name="Summary", index=False)
        data_pd.to_excel(writer, sheet_name="Data", index=False)

        # Auto-fit columns for Summary sheet
        def _autofit_columns(*, worksheet, dataframe):
            for idx, col in enumerate(dataframe.columns):
                series = dataframe[col]
                max_len = (
                    max(series.astype(str).map(len).max(), len(str(series.name))) + 2
                )
                worksheet.set_column(idx, idx, max_len)

        summary_worksheet = writer.sheets["Summary"]
        _autofit_columns(worksheet=summary_worksheet, dataframe=summary_pd)

        # Auto-fit columns for Data sheet
        data_worksheet = writer.sheets["Data"]
        _autofit_columns(worksheet=data_worksheet, dataframe=data_pd)

        # Auto-filter the data sheet
        data_worksheet.autofilter(0, 0, data_pd.shape[0], data_pd.shape[1] - 1)

        # Freeze the first row of the data sheet
        data_worksheet.freeze_panes(1, 0)

    excel_buffer.seek(0)
    report_date = now_utc.strftime("%Y%m%d")
    project_name_long = project.name_long.replace(" ", "_")
    filename = f"SCADA_Telemetry_Last_Reported_{project_name_long}_{report_date}.xlsx"

    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
