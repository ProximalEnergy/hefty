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
    - Summary sheet: Report Generated, Project Name, Non-Ghost/Ghost tag
      counts, and Fresh/Stale/Never for each (6 rows).
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
    df: pl.DataFrame = await DbQuery(query=stmt).get_async(schema=project.name_short)
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

    # Calculate summary statistics (non-ghost vs ghost, then status breakdown)
    not_ghost = ~pl.col("Ghost")
    summary_counts = df.select(
        non_ghost_tags=not_ghost.sum(),
        ghost_tags=pl.col("Ghost").sum(),
        non_ghost_fresh=(not_ghost & (pl.col("Status") == "Fresh")).sum(),
        non_ghost_stale=(not_ghost & (pl.col("Status") == "Stale")).sum(),
        non_ghost_never=(not_ghost & (pl.col("Status") == "Never")).sum(),
        ghost_fresh=(pl.col("Ghost") & (pl.col("Status") == "Fresh")).sum(),
        ghost_stale=(pl.col("Ghost") & (pl.col("Status") == "Stale")).sum(),
        ghost_never=(pl.col("Ghost") & (pl.col("Status") == "Never")).sum(),
    ).row(0)
    (
        non_ghost_tags,
        ghost_tags,
        non_ghost_fresh,
        non_ghost_stale,
        non_ghost_never,
        ghost_fresh,
        ghost_stale,
        ghost_never,
    ) = summary_counts

    # Summary rows: first two are text, rest are integers (written as numbers in
    # Excel with number format to avoid "Number Stored as Text" warning).
    summary_metrics = [
        "Report Generated",
        "Project Name",
        "Non-Ghost Tags",
        "Non-Ghost Fresh",
        "Non-Ghost Stale",
        "Non-Ghost Never",
        "Ghost Tags",
        "Ghost Fresh",
        "Ghost Stale",
        "Ghost Never",
    ]
    summary_values: list[str | int] = [
        now_utc.strftime("%Y-%m-%d %H:%M UTC"),
        project.name_long,
        non_ghost_tags,
        non_ghost_fresh,
        non_ghost_stale,
        non_ghost_never,
        ghost_tags,
        ghost_fresh,
        ghost_stale,
        ghost_never,
    ]

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

    def _autofit_columns(*, worksheet, dataframe):
        """Set each column's width to fit its longest value.

        Args:
            worksheet: The xlsxwriter Worksheet object to apply column widths
                to.
            dataframe: The pandas DataFrame whose column data determines the
                required widths.
        """
        for idx, col in enumerate(dataframe.columns):
            series = dataframe[col]
            max_len = max(series.astype(str).map(len).max(), len(str(series.name))) + 2
            worksheet.set_column(idx, idx, max_len)

    with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
        book = writer.book
        num_fmt = book.add_format({"num_format": "#,##0"})
        summary_ws = book.add_worksheet("Summary")
        # Write Summary sheet row by row so numeric cells are write_number (not
        # text), avoiding "Number Stored as Text" warning in Excel.
        for row_idx, (metric, value) in enumerate(
            zip(summary_metrics, summary_values, strict=True)
        ):
            summary_ws.write_string(row_idx, 0, metric)
            if row_idx < 2:
                summary_ws.write_string(row_idx, 1, str(value))
            else:
                summary_ws.write_number(row_idx, 1, value, num_fmt)
        width_metric = max(len(m) for m in summary_metrics) + 2
        width_val = (
            max(
                len(str(v)) if isinstance(v, str) else len(f"{v:,}")
                for v in summary_values
            )
            + 2
        )
        summary_ws.set_column(0, 0, width_metric)
        summary_ws.set_column(1, 1, width_val, num_fmt)

        data_pd.to_excel(writer, sheet_name="Data", index=False)
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
