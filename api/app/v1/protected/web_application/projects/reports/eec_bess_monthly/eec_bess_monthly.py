import asyncio
import datetime
import os
import shutil
import tempfile
from collections.abc import Callable
from html import escape
from typing import cast
from zoneinfo import ZoneInfo

import aiohttp
import boto3
import numpy as np
import pandas as pd
from core.crud.operational.contract_kpis import (
    get_contract_kpis as crud_get_contract_kpis,
)
from core.crud.operational.failure_modes import (
    get_failure_modes as crud_get_failure_modes,
)
from core.crud.operational.kpi_data import get_kpi_data as crud_get_kpi_data
from core.crud.operational.qse_integrations import (
    get_qse_integration_by_project_id as crud_get_qse_integration_by_project_id,
)
from core.crud.project import events as crud_project_events
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.crud.project.devices import (
    get_project_devices_async as crud_get_project_devices_async,
)
from core.db_query import OutputType
from core.enumerations import DeviceType, KPIType, TimeInterval
from pydantic import BaseModel
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepInFrame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from scipy.stats import linregress
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from core import models

from .chart_utils import create_stacked_bar_chart, create_waterfall_chart
from .report_utils import (
    PLACEHOLDER_PNG_BYTES,
    calc_delta_percentage,
    format_change_text,
    format_change_text_reversed,
    format_dollar_per_kw_value,
    format_dollar_value,
    format_energy_value,
    format_percentage_per_year,
    format_percentage_value,
    img_fit_by_width,
    load_image_from_source,
    tstyle_gridded_table,
)


class BESSMonthlyReportStrategy(BaseModel):
    """BESS monthly report strategy data."""

    name: str
    month_value: float | None = None
    ytd_value: float | None = None
    vs_perfect: float | None = None


class BESSMonthlySmartBidderMetric(BaseModel):
    """SmartBidder metric values for the BESS monthly report."""

    actual: float | None = None
    expected: float | None = None


class BESSMonthlyReportRequest(BaseModel):
    """BESS monthly report generation request."""

    month: datetime.date
    strategies: list[BESSMonthlyReportStrategy]
    operational_commentary: str | None = None
    smart_bidder_metrics: dict[str, BESSMonthlySmartBidderMetric] | None = None


# ---------------------------------------------------------------------------
# Global layout & assets
# ---------------------------------------------------------------------------

MARGIN_X = 0.25 * inch
MARGIN_TOP = 0.75 * inch
MARGIN_BOTTOM = 0.50 * inch
GUTTER_PT = 10  # whitespace between columns in multi-col tables
WATERMARK_ALPHA = 0.12
# WATERMARK_TEXT_MAIN = "CONFIDENTIAL"
# WATERMARK_TEXT_SUB = "DRAFT"
ERCOT_LOSS_PER_DAY = 0.357

PWD = os.path.dirname(os.path.abspath(__file__))
RESOURCES_DIR = os.path.join(os.path.dirname(PWD), "resources")
ASSETS = {
    "proximal_logo": os.path.join(RESOURCES_DIR, "proximal_logo.png"),
    "client_logo": os.path.join(RESOURCES_DIR, "excelsior_logo.png"),
    "placeholder": os.path.join(RESOURCES_DIR, "placeholder_logo.png"),
}

# ---------------------------------------------------------------------------
# Placeholder images
# ---------------------------------------------------------------------------

# Executive KPI Index (radar) chart PNG bytes. Replace with real bytes once the
# radar chart generation is implemented.
radar_png = PLACEHOLDER_PNG_BYTES

# ---------------------------------------------------------------------------
# Style system
# ---------------------------------------------------------------------------


def build_styles():
    """Return a dict of ParagraphStyles used throughout the report."""
    base = getSampleStyleSheet()

    # compact body bases (no inherited extra spacing)
    base8 = ParagraphStyle(
        "base8",
        fontName="Helvetica",
        fontSize=8,
        leading=9,
        spaceBefore=0,
        spaceAfter=0,
    )
    base9 = ParagraphStyle(
        "base9",
        fontName="Helvetica",
        fontSize=9,
        leading=10.5,
        spaceBefore=0,
        spaceAfter=0,
    )

    styles = {
        "h2_center": ParagraphStyle("h2_center", parent=base["Heading2"], alignment=1),
        "body": base["BodyText"],
        "body_center": ParagraphStyle(
            "body_center", parent=base["BodyText"], alignment=1
        ),
        # 8pt compact variants for dense tables
        "label8i": ParagraphStyle(
            "label8i", parent=base8, fontName="Helvetica-Oblique"
        ),
        "val8": ParagraphStyle("val8", parent=base8, alignment=2),
        "val8b": ParagraphStyle(
            "val8b", parent=base8, alignment=2, fontName="Helvetica-Bold"
        ),
        "hdr8": ParagraphStyle(
            "hdr8", parent=base8, alignment=1, fontName="Helvetica-Bold"
        ),
        # 9pt compact variants (three-column metrics section)
        "label9i": ParagraphStyle(
            "label9i", parent=base9, fontName="Helvetica-Oblique"
        ),
        "val9": ParagraphStyle("val9", parent=base9, alignment=2),
        "val9b": ParagraphStyle(
            "val9b", parent=base9, alignment=2, fontName="Helvetica-Bold"
        ),
        "hsub9": ParagraphStyle(
            "hsub9", parent=base9, alignment=1, fontName="Helvetica-Bold"
        ),
    }
    return styles


# ---------------------------------------------------------------------------
# Canvas helpers
# ---------------------------------------------------------------------------


# The doc argument is not used in this function, but it is required by the
# draw_header_footer function signature.
def draw_header_footer(c: canvas.Canvas, doc):  # noqa: ARG001 # nosemgrep: python-enforce-keyword-only-args
    """Logos flush to the top; simple footer w/ generation date & mark."""
    width, height = A4

    # header logos - define the height and let the images maintain their aspect ratio
    logo_h = inch / 3
    proximal_img = Image(ASSETS["proximal_logo"])
    proximal_w = proximal_img.imageWidth * logo_h / proximal_img.imageHeight
    c.drawImage(
        ASSETS["proximal_logo"],
        MARGIN_X,
        height - logo_h - (MARGIN_TOP - logo_h) / 2.0,
        width=proximal_w,
        height=logo_h,
        preserveAspectRatio=True,
        mask="auto",
    )
    client_img = Image(ASSETS["client_logo"])
    client_w = client_img.imageWidth * logo_h / client_img.imageHeight
    c.drawImage(
        ASSETS["client_logo"],
        width - MARGIN_X - client_w,
        height - logo_h - (MARGIN_TOP - logo_h) / 2.0,
        width=client_w,
        height=logo_h,
        preserveAspectRatio=True,
        mask="auto",
    )

    # footer
    c.setFont("Helvetica", 9)
    c.drawCentredString(
        width / 2.0,
        0.10 * inch,
        "Generated " + datetime.datetime.now().strftime("%m/%d/%Y"),
    )


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


async def section_project_details(
    *,
    doc,
    project: models.Project,
):
    """Create project details section with name, size, location, and address.

    Args:
        doc: Document template.
        project: Project model instance.

    Returns:
        List of flowable elements.
    """
    col_ratios = [1, 0.75, 2]
    max_width = doc.width - 2 * MARGIN_X
    col_widths = [max_width * r / sum(col_ratios) for r in col_ratios]

    project_table = Table(
        [
            ["Project Name", "Size (kW-AC)", "Site Address"],
            [
                project.name_long,
                f"{(project.poi * 1000):,.0f}",
                project.address,
            ],
        ],
        colWidths=col_widths,
    )
    project_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    return [project_table, Spacer(1, 0.20 * inch)]


def section_operational_commentary(*, styles, commentary: str):
    """Create operational commentary section.

    Args:
        styles: Style dictionary.
        commentary: Commentary text.

    Returns:
        List of flowable elements.
    """
    title = Paragraph("<b>Operational Commentary</b>", styles["h2_center"])
    normalized_commentary = (
        escape(commentary).replace("\r\n", "\n").replace("\n", "<br />")
    )
    body = Paragraph(
        normalized_commentary,
        styles["body"],
    )
    return [title, body, Spacer(1, 0.30 * inch)]


def section_strategy_table_with_image(
    *, doc, styles, strategies: list[BESSMonthlyReportStrategy], month: datetime.date
):
    """Create strategy performance comparison section with table and image.

    Args:
        doc: Document template.
        styles: Style dictionary.
        strategies: List of strategy objects with performance data.
        month: Month to display in the table.
    Returns:
        List of flowable elements.
    """
    # Title & styles
    tbl_title = Paragraph(
        "<para align='center'><b>Strategy Performance Comparison</b></para>",
        styles["body"],
    )

    # Small 8pt typography for dense table
    label8i, val8, val8b, hdr8 = (
        styles["label8i"],
        styles["val8"],
        styles["val8b"],
        styles["hdr8"],
    )

    # Header row + body
    data = [
        [
            Paragraph("", styles["body"]),
            Paragraph(month.strftime("%b-%Y"), hdr8),
            Paragraph("Year to Date:", hdr8),
            Paragraph("vs Perfect Foresight:", hdr8),
        ]
    ]
    rows = [
        (
            a.name,
            f"${a.month_value:,.0f}" if a.month_value is not None else "—",
            f"${a.ytd_value:,.0f}" if a.ytd_value is not None else "—",
            f"{a.vs_perfect:.2%}" if a.vs_perfect is not None else "—",
            True if a.name == "Active Strategy" else False,
        )
        for a in strategies
    ]
    for label, v1, v2, v3, bold in rows:
        data.append(
            [
                Paragraph(f"{label}:", label8i),
                Paragraph(v1, val8b if bold else val8),
                Paragraph(v2, val8b if bold else val8),
                Paragraph(v3, val8b if bold else val8),
            ]
        )

    perf_tbl = Table(
        data,
        colWidths=[1.3 * inch, 0.75 * inch, 0.75 * inch, 1.25 * inch],
        hAlign="CENTER",
    )
    perf_tbl.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (1, 0), (-1, 0), 1.5, colors.black),  # header underline
                ("LINEBEFORE", (2, 0), (2, -1), 1.2, colors.black),  # vertical divider
                ("LINEBEFORE", (3, 0), (3, -1), 1.2, colors.black),  # vertical divider
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),  # values right
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ]
        )
    )

    # footnote = Paragraph(
    #     "<para align='center'><font name='Helvetica-Oblique' size='8'>"
    #     "These fields will be user-input until we have Ascend integration."
    #     "</font></para>",
    #     styles["body"],
    # )

    content_block = KeepInFrame(
        doc.width,
        6.2 * inch,
        [
            tbl_title,
            Spacer(1, 0.10 * inch),
            perf_tbl,
            Spacer(1, 0.08 * inch),
        ],  # footnote],
        mode="shrink",
        hAlign="CENTER",
        vAlign="TOP",
    )
    return [content_block, Spacer(1, 0.30 * inch)]


def section_full_width_image(*, doc, img_bytes_or_path, styles, caption=None):
    """Create a full-width image section with optional caption.

    Args:
        doc: Document template.
        img_bytes_or_path: Image source (str path, bytes, or BytesIO).
        styles: Style dictionary.
        caption: Optional caption text.

    Returns:
        List of flowable elements.
    """
    max_w = doc.width - 2 * MARGIN_X
    img = load_image_from_source(img_bytes_or_path)
    img = img_fit_by_width(img=img, target_w=max_w)
    flows = [img, Spacer(1, 0.30 * inch)]
    if caption:
        flows.append(
            Paragraph(
                f"<para align='center'><font name='Helvetica-Oblique' size='8'>{caption}</font></para>",  # noqa: E501
                styles["body"],
            )
        )
    return flows


def section_revenue_breakdown_with_table(
    *, doc, img_bytes_or_path, rev_breakdown_df, styles
):
    """Create revenue breakdown section with chart and summary table.

    Args:
        doc: Document template.
        img_bytes_or_path: Chart image source (str path, bytes, or BytesIO).
        rev_breakdown_df: DataFrame with daily revenue breakdown data.
        styles: Style dictionary.

    Returns:
        List of flowable elements.
    """
    max_w = doc.width - 2 * MARGIN_X

    # Add the image
    img = load_image_from_source(img_bytes_or_path)
    img = img_fit_by_width(img=img, target_w=max_w)
    flows = [img, Spacer(1, 0.20 * inch)]

    # Aggregate daily data by month
    series_monthly = rev_breakdown_df.set_index("index").sum()

    # Create table with months as rows and services as columns
    # Prepare data: months as rows, service types as columns
    service_columns = [
        "Real-Time Energy",
        "Day-Ahead Energy",
        "Ancillary Services",
        "Misc Charges",
        "Net Profit",
    ]
    service_labels = [col.replace("_", " ") for col in service_columns]

    # Build table data
    table_data = []

    # Header row
    header_row = service_labels
    table_data.append([Paragraph(cell, styles["hdr8"]) for cell in header_row])

    # Data rows - format values
    value_style = styles["val8"]  # Right align values

    row_data = []
    col_format = {
        x: y
        for x, y in zip(
            service_columns,
            [
                f"{'-' if series_monthly[x] < 0 else ''}${abs(series_monthly[x]):,.2f}"
                for x in service_columns
            ],
        )
    }

    for key, value in series_monthly.items():
        formatted_value = col_format[key]
        row_data.append(Paragraph(formatted_value, value_style))

    table_data.append(row_data)

    # Calculate column widths
    num_cols = len(header_row)
    service_col_width = max_w / num_cols
    col_widths = [service_col_width] * num_cols

    # Create table
    revenue_table = Table(table_data, colWidths=col_widths)
    base_style = tstyle_gridded_table(
        header_bg=colors.lightgrey,
        row_bg_alt=colors.HexColor("#F7F7F7"),
    )
    # Add additional styling specific to this table
    revenue_table.setStyle(base_style)
    revenue_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),  # All columns right-aligned
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )

    flows.append(revenue_table)
    flows.append(Spacer(1, 0.30 * inch))

    return flows


def metric_table(*, rows, width, label_style, value_style, include_header=True):
    """Create a metric table with actual, expected, and delta columns.

    Args:
        rows: List of (metric_name, actual, expected, delta) tuples.
        width: Total table width in points.
        label_style: ParagraphStyle for metric labels.
        value_style: ParagraphStyle for values.
        include_header: Whether to include header row.

    Returns:
        Table with metric data.
    """
    col_widths = [
        0.40 * width,  # Metric
        0.20 * width,  # Actual
        0.20 * width,  # Expected
        0.20 * width,  # Delta
    ]

    data = []

    if include_header:
        data.append(
            [
                Paragraph("Metric", label_style),  # LEFT
                Paragraph("<para alignment='right'>Actual</para>", label_style),
                Paragraph("<para alignment='right'>Expected</para>", label_style),
                Paragraph("<para alignment='right'>Δ vs Expected</para>", label_style),
            ]
        )

    for metric, actual, expected, delta in rows:
        data.append(
            [
                Paragraph(metric, label_style),
                Paragraph(actual, value_style),
                Paragraph(expected, value_style),
                Paragraph(delta, value_style),
            ]
        )

    tbl = Table(data, colWidths=col_widths, hAlign="LEFT")

    tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),  # Metric column
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),  # All other columns
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )

    return tbl


def section_two_column_metrics(
    *,
    doc,
    styles,
    kpi_sums,
    kpi_means,
    soc_stats,
    kpi_expected_values,
    request,
    current_soh,
):
    """Create two-column metrics section (BESS SOC and SmartBidder metrics).

    Args:
        doc: Document template.
        styles: Style dictionary.
        kpi_sums: Dictionary of KPI sums by type ID.
        kpi_means: Dictionary of KPI means by type ID.
        soc_stats: Dictionary with soc_min and soc_max.
        kpi_expected_values: Dictionary of expected KPI values.
        request: BESSMonthlyReportRequest object.
        current_soh: Current SOH value.
    Returns:
        List of flowable elements.
    """
    # two equal columns with a fixed gutter in between
    left_w = (doc.width - GUTTER_PT) / 2.0
    right_w = left_w

    # calc_delta is now imported from report_utils as calc_delta_percentage

    # ---- data ----
    kpi_rows = [
        # Metric name | Actual | Expected | Δ vs Expected
        (
            "Monthly Cycles",
            f"{kpi_sums[KPIType.BESS_STRING_CYCLE_COUNT]:.2f}",
            f"{kpi_expected_values['monthly_cycles']:.2f}",
            calc_delta_percentage(
                actual=kpi_sums[KPIType.BESS_STRING_CYCLE_COUNT],
                expected=kpi_expected_values["monthly_cycles"],
            ),
        ),  # source: BESS Bank Cycle Count KPI
        (
            "YTD Cycles",
            "—",
            f"{kpi_expected_values['ytd_cycles']:.2f}",
            calc_delta_percentage(
                actual=kpi_sums[KPIType.BESS_STRING_CYCLE_COUNT],
                expected=kpi_expected_values["ytd_cycles"],
            ),
        ),  # source: BESS Bank Cycle Count KPI
        (
            "Lifetime Cycles",
            "—",
            "—",
            "—",
        ),  # source: BESS Bank Cycle Count KPI
        (
            "BESS State of Health (%)",
            format_percentage_value(value=kpi_means[KPIType.BESS_STRING_SOH]),
            format_percentage_value(value=current_soh),
            calc_delta_percentage(
                actual=kpi_means[KPIType.BESS_STRING_SOH],
                expected=current_soh,
            ),
        ),  # source: BESS Bank SoH KPI
        (
            "Average SOC (%)",
            format_percentage_value(
                value=kpi_means[KPIType.PROJECT_AVERAGE_SOC_PERCENT]
            ),
            format_percentage_value(value=kpi_expected_values["average_soc"]),
            calc_delta_percentage(
                actual=kpi_means[KPIType.PROJECT_AVERAGE_SOC_PERCENT],
                expected=kpi_expected_values["average_soc"],
            ),
        ),  # source: Project Average SOC KPI
        (
            "Average Resting SOC (%)",
            format_percentage_value(
                value=kpi_means[KPIType.BESS_STRING_RESTING_SOC_PERCENT]
            ),
            format_percentage_value(value=kpi_expected_values["average_resting_soc"]),
            calc_delta_percentage(
                actual=kpi_means[KPIType.BESS_STRING_RESTING_SOC_PERCENT],
                expected=kpi_expected_values["average_resting_soc"],
            ),
        ),  # source: BESS Bank Resting SOC KPI
        (
            "Minimum SOC (%)",
            format_percentage_value(value=soc_stats["soc_min"]),
            format_percentage_value(value=kpi_expected_values["min_soc"]),
            calc_delta_percentage(
                actual=soc_stats["soc_min"],
                expected=kpi_expected_values["min_soc"],
            ),
        ),  # source: Minimum SOC KPI
        (
            "Maximum SOC (%)",
            format_percentage_value(value=soc_stats["soc_max"]),
            format_percentage_value(value=kpi_expected_values["max_soc"]),
            calc_delta_percentage(
                actual=soc_stats["soc_max"],
                expected=kpi_expected_values["max_soc"],
            ),
        ),  # source: Maximum SOC KPI
    ]

    # TODO: Replace hardcoded SmartBidder metrics with real data
    # These should come from project configuration or SmartBidder API
    sb_rows = []
    if request.smart_bidder_metrics:
        for name, item in request.smart_bidder_metrics.items():
            sb_rows.append(
                (
                    name,
                    f"{item.actual:.3f}" if item.actual is not None else "—",
                    f"{item.expected:.3f}" if item.expected is not None else "—",
                    (
                        f"{((item.actual - item.expected) / item.expected):.2%}"
                        if (
                            item.actual is not None
                            and item.expected is not None
                            and item.expected != 0
                        )
                        else "—"
                    ),
                )
            )

    # ---- tables ----
    kpi_tbl = metric_table(
        rows=kpi_rows,
        width=left_w,
        label_style=styles["label9i"],
        value_style=styles["val9"],
    )
    sb_tbl = metric_table(
        rows=sb_rows,
        width=right_w,
        label_style=styles["label9i"],
        value_style=styles["val9"],
    )

    # ---- column blocks ----
    left_block = KeepInFrame(
        left_w,
        6 * inch,
        [
            Paragraph("BESS Operational Metrics", styles["h2_center"]),
            Spacer(1, 6),
            kpi_tbl,
        ],
        mode="shrink",
        hAlign="LEFT",
        vAlign="TOP",
    )
    right_block = KeepInFrame(
        right_w,
        6 * inch,
        [
            Paragraph("BESS SmartBidder Metrics", styles["h2_center"]),
            Spacer(1, 6),
            sb_tbl,
        ],
        mode="shrink",
        hAlign="LEFT",
        vAlign="TOP",
    )

    # ---- outer layout: [left][gutter][right] ----
    outer = Table(
        [[left_block, "", right_block]], colWidths=[left_w, GUTTER_PT, right_w]
    )
    outer.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return [outer]


def section_monthly_comparison(*, doc, styles, executive_summary_df: pd.DataFrame):
    """Create monthly executive summary comparison table.

    Args:
        doc: Document template.
        styles: Style dictionary.
        executive_summary_df: DataFrame with metrics and deltas.

    Returns:
        List of flowable elements.
    """
    title = Paragraph("<b>Monthly Executive Summary</b>", styles["h2_center"])

    # --- Define styles ---
    cell_style = ParagraphStyle(
        "cell",
        parent=styles["body"],
        fontName="Helvetica",
        fontSize=10,
        leading=12,
        spaceBefore=0,
        spaceAfter=0,
    )
    bold_center = ParagraphStyle(
        "bold_center",
        parent=cell_style,
        fontName="Helvetica-Bold",
        alignment=1,  # center
    )
    right_style = ParagraphStyle(
        "right_style",
        parent=cell_style,
        alignment=2,  # right align
    )

    # Formatting functions are now imported from report_utils

    def _cell_float(row: str, column: str) -> float:
        coerced = pd.to_numeric(
            executive_summary_df.loc[row, column],
            errors="coerce",
        )
        return float(coerced)

    def _delta_str(row: str) -> str:
        return str(executive_summary_df.loc[row, "Delta"])

    # --- Table Data (now 4 columns) ---
    executive_data: list[list[str]] = [
        ["Metric", "This Month", "Expected", "Δ vs Expected"],
        [
            "Total Revenue",
            format_dollar_value(value=_cell_float("Total Revenue", "This Month")),
            format_dollar_value(value=_cell_float("Total Revenue", "Expected")),
            _delta_str("Total Revenue"),
        ],
        [
            "Total Energy Delivered",
            format_energy_value(
                value=_cell_float("Total Energy Delivered", "This Month")
            ),
            format_energy_value(
                value=_cell_float("Total Energy Delivered", "Expected")
            ),
            _delta_str("Total Energy Delivered"),
        ],
        [
            "Average Capacity Factor",
            format_percentage_value(
                value=_cell_float("Average Capacity Factor", "This Month")
            ),
            format_percentage_value(
                value=_cell_float("Average Capacity Factor", "Expected")
            ),
            _delta_str("Average Capacity Factor"),
        ],
        [
            "Capacity-Weighted Availability",
            format_percentage_value(
                value=_cell_float("Capacity-Weighted Availability", "This Month")
            ),
            format_percentage_value(
                value=_cell_float("Capacity-Weighted Availability", "Expected")
            ),
            _delta_str("Capacity-Weighted Availability"),
        ],
        [
            "Degradation Rate",
            format_percentage_per_year(_cell_float("Degradation Rate", "This Month")),
            format_percentage_per_year(_cell_float("Degradation Rate", "Expected")),
            _delta_str("Degradation Rate"),
        ],
        [
            "Forecast Accuracy",
            format_percentage_value(
                value=_cell_float("Forecast Accuracy", "This Month")
            ),
            format_percentage_value(value=_cell_float("Forecast Accuracy", "Expected")),
            _delta_str("Forecast Accuracy"),
        ],
    ]

    # Convert all rows to Paragraphs
    formatted_rows: list[list[Paragraph]] = []
    for i, row in enumerate(executive_data):
        if i == 0:  # header row
            formatted_rows.append(
                [
                    Paragraph(row[0], bold_center),
                    Paragraph(row[1], bold_center),
                    Paragraph(row[2], bold_center),
                    Paragraph(row[3], bold_center),
                ]
            )
        elif i == 5:  # degradation rate row
            formatted_rows.append(
                [
                    Paragraph(row[0], cell_style),  # Metric (left)
                    Paragraph(row[1], right_style),  # This Month
                    Paragraph(row[2], right_style),  # Expected
                    Paragraph(
                        format_change_text_reversed(row[3]), right_style
                    ),  # Delta
                ]
            )
        else:
            formatted_rows.append(
                [
                    Paragraph(row[0], cell_style),  # Metric (left)
                    Paragraph(row[1], right_style),  # This Month
                    Paragraph(row[2], right_style),  # Expected
                    Paragraph(format_change_text(row[3]), right_style),  # Delta
                ]
            )

    # --- Table formatting ---
    executive_table = Table(
        formatted_rows,
        colWidths=[
            doc.width * 0.40,  # Metric
            doc.width * 0.20,  # This Month
            doc.width * 0.20,  # Expected
            doc.width * 0.20,  # Δ vs Expected
        ],
    )
    base_style = tstyle_gridded_table(
        header_bg=colors.lightgrey,
        row_bg_alt=colors.HexColor("#F7F7F7"),
    )
    executive_table.setStyle(base_style)

    return [
        title,
        Spacer(1, 0.1 * inch),
        executive_table,
        Spacer(1, 0.2 * inch),
    ]


def section_tbx_comparison(*, doc, styles, monthly_tbx: dict[str, float]):
    """Create tbx comparison section.

    Args:
        doc: Document template.
        styles: Style dictionary.
        monthly_tbx: Dictionary with monthly tbx data.
    """
    title = Paragraph("<b>TB-X Comparison</b>", styles["h2_center"])
    cell_style = ParagraphStyle(
        "tbx_cell",
        parent=styles["body"],
        fontName="Helvetica",
        fontSize=10,
        leading=12,
        spaceBefore=0,
        spaceAfter=0,
    )
    header_style = ParagraphStyle(
        "tbx_header",
        parent=cell_style,
        fontName="Helvetica-Bold",
        alignment=1,
    )
    right_style = ParagraphStyle(
        "tbx_right",
        parent=cell_style,
        alignment=2,
    )

    def format_or_dash(
        *, value: float | None, formatter: Callable[[float], str]
    ) -> str:
        if value is None:
            return "—"
        return formatter(value)

    realized_intraday_value = monthly_tbx.get("realized_intraday_value")
    tb1_raw = monthly_tbx.get("1")
    tb2_raw = monthly_tbx.get("2")
    tb4_raw = monthly_tbx.get("4")

    realized_val = format_or_dash(
        value=realized_intraday_value, formatter=format_dollar_per_kw_value
    )
    tb1_val = format_or_dash(value=tb1_raw, formatter=format_dollar_per_kw_value)
    tb2_val = format_or_dash(value=tb2_raw, formatter=format_dollar_per_kw_value)
    tb4_val = format_or_dash(value=tb4_raw, formatter=format_dollar_per_kw_value)

    def safe_pct_capture(*, expected: float | None, actual: float | None) -> str:
        if expected is None or actual is None or expected == 0:
            return "—"
        return format_percentage_value(value=max(actual / expected, 0))

    tb1_delta = safe_pct_capture(expected=tb1_raw, actual=realized_intraday_value)
    tb2_delta = safe_pct_capture(expected=tb2_raw, actual=realized_intraday_value)
    tb4_delta = safe_pct_capture(expected=tb4_raw, actual=realized_intraday_value)

    table_rows = [
        [
            Paragraph("Metric", header_style),
            Paragraph("Value", header_style),
            Paragraph("TB Capture", header_style),
        ],
        [
            Paragraph("Realized Intraday Value", cell_style),
            Paragraph(realized_val, right_style),
            Paragraph("—", right_style),
        ],
        [
            Paragraph("TB-1", cell_style),
            Paragraph(tb1_val, right_style),
            Paragraph(tb1_delta, right_style),
        ],
        [
            Paragraph("TB-2", cell_style),
            Paragraph(tb2_val, right_style),
            Paragraph(tb2_delta, right_style),
        ],
        [
            Paragraph("TB-4", cell_style),
            Paragraph(tb4_val, right_style),
            Paragraph(tb4_delta, right_style),
        ],
    ]

    table = Table(
        table_rows,
        colWidths=[doc.width * 0.45, doc.width * 0.30, doc.width * 0.25],
        hAlign="LEFT",
    )
    table_style = tstyle_gridded_table(
        header_bg=colors.lightgrey,
        row_bg_alt=colors.HexColor("#F7F7F7"),
    )
    table.setStyle(table_style)

    return [title, Spacer(1, 0.10 * inch), table, Spacer(1, 0.20 * inch)]


def section_events_overview(*, doc, styles, image_bytes, rollup_rows, event_table):
    """Create events overview section with chart, summary, and detail tables.

    Args:
        doc: Document template.
        styles: Style dictionary.
        image_bytes: Chart image bytes.
        rollup_rows: List of summary metric rows.
        event_table: DataFrame of top events with metadata.

    Returns:
        List of flowable elements.
    """
    max_w = doc.width - 2 * MARGIN_X
    title = Paragraph(
        "<para align='center'>Availability & Production-Impacting Events</para>",
        styles["h2_center"],
    )

    img = load_image_from_source(image_bytes)
    img = img_fit_by_width(img=img, target_w=max_w)
    # events table

    def build_events_table():
        # --- cell styles that actually wrap ---
        cell_left = ParagraphStyle(
            "cell_left",
            parent=styles["body"],
            alignment=TA_LEFT,
            wordWrap="CJK",  # allows breaking long tokens
            splitLongWords=1,
        )
        cell_center = ParagraphStyle(
            "cell_center",
            parent=styles["body"],
            alignment=TA_CENTER,
            wordWrap="CJK",
            splitLongWords=1,
        )
        cell_right = ParagraphStyle(
            "cell_right",
            parent=styles["body"],
            alignment=TA_RIGHT,
            wordWrap="CJK",
            splitLongWords=1,
        )
        header_style = ParagraphStyle(
            "header_style",
            parent=styles["body"],
            alignment=TA_CENTER,
            wordWrap="CJK",
            splitLongWords=1,
            fontName="Helvetica-Bold",
        )

        def paragraph_cell(text: str, *, align: str = "left"):
            safe_text = escape(str(text))
            style = {"left": cell_left, "center": cell_center, "right": cell_right}[
                align
            ]
            return Paragraph(safe_text, style)

        def header_cell(*, text: str):
            return Paragraph(escape(str(text)), header_style)

        # --- build data ---
        if event_table is not None and not event_table.empty:
            df = event_table.copy()

            sort_cols = [c for c in df.columns if c.lower().startswith("capacity loss")]
            if sort_cols:
                df = df.sort_values(by=sort_cols, ascending=False)

            def fmt_dt(*, val):
                if pd.isna(val):
                    return "—"
                try:
                    return pd.Timestamp(val).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    return str(val)

            def fmt_val(*, val, is_currency: bool = False):
                if pd.isna(val):
                    return "—"
                try:
                    num = float(val)
                    return f"${num:,.2f}" if is_currency else f"{num:,.2f}"
                except (ValueError, TypeError):
                    return str(val)

            header = list(df.columns)
            events_data = [[header_cell(text=c) for c in header]]

            for _, row in df.iterrows():
                formatted_row = []
                for col in df.columns:
                    lower_col = col.lower()
                    value = row[col]

                    if "start" in lower_col or "end" in lower_col:
                        formatted_row.append(paragraph_cell(fmt_dt(val=value)))
                    elif "financial" in lower_col:
                        formatted_row.append(
                            paragraph_cell(
                                fmt_val(val=value, is_currency=True), align="right"
                            )
                        )
                    elif "loss" in lower_col:
                        formatted_row.append(
                            paragraph_cell(fmt_val(val=value), align="right")
                        )
                    else:
                        formatted_row.append(
                            paragraph_cell(value if value is not None else "—")
                        )

                events_data.append(formatted_row)

        else:
            events_data = [
                [
                    header_cell(text="Device Name"),
                    header_cell(text="Failure Mode"),
                    header_cell(text="Start Time"),
                    header_cell(text="End Time"),
                    header_cell(text="Financial Loss ($)"),
                ],
                [
                    paragraph_cell("No events available"),
                    paragraph_cell("—"),
                    paragraph_cell("—"),
                    paragraph_cell("—"),
                    paragraph_cell("—", align="right"),
                ],
            ]

        # --- span printable area exactly ---
        col_count = len(events_data[0])
        col_fracs = [0.24, 0.30, 0.16, 0.16, 0.14]  # sums to 1.0
        if col_count > len(col_fracs):
            col_fracs.extend([0.14] * (col_count - len(col_fracs)))

        col_widths = [doc.width * f for f in col_fracs[:col_count]]

        events_tbl = Table(
            events_data,
            colWidths=col_widths,
            hAlign="CENTER",
            repeatRows=1,  # repeat header if table splits
            splitByRow=1,
        )

        base_style = tstyle_gridded_table(
            header_bg=colors.whitesmoke,
            row_bg_alt=colors.HexColor("#F5F5F5"),
        )
        events_tbl.setStyle(base_style)

        events_tbl.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )

        # IMPORTANT: no KeepInFrame shrink
        return events_tbl

    events_tbl = build_events_table()

    rollup_tbl = Table(rollup_rows, colWidths=[3.0 * inch, 2.0 * inch])
    rollup_tbl.setStyle(
        tstyle_gridded_table(
            header_bg=None,
            row_bg_alt=colors.HexColor("#F5F5F5"),
        )
    )
    rollup_disclaimer = Paragraph(
        "<font name='Helvetica-Oblique' size='8'><sup>*</sup> Financial impact is calculated using an average loss of $0.357/kW/day in ERCOT. This is a rough estimate based on annualized data, and the Proximal team is working to improve the calculation methodology.</font>",  # noqa: E501
        styles["body"],
    )
    if int([x for x in rollup_rows if x[0] == "Total Events"][0][1]) > 10:
        event_table_title = (
            "<para align='center'>Individual Event Details (top 10 shown)</para>"
        )
    else:
        event_table_title = "<para align='center'>Individual Event Details</para>"

    return [
        title,
        Spacer(1, 0.20 * inch),
        img,
        Spacer(1, 0.30 * inch),
        Paragraph("<para align='center'>Event Summary Metrics</para>", styles["body"]),
        rollup_tbl,
        rollup_disclaimer,
        Spacer(1, 0.20 * inch),
        Paragraph(event_table_title, styles["body"]),
        events_tbl,
    ]


def section_no_events_overview(
    *, doc, styles, message: str = "No Events detected this month."
):
    """Render a notice when no event data is available for the reporting period."""
    title = Paragraph(
        "<para align='center'>Availability & Production-Impacting Events</para>",
        styles["h2_center"],
    )
    content = Table(
        [[Paragraph(message, styles["body_center"])]],
        colWidths=[doc.width],
        hAlign="CENTER",
    )
    content.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#C7D2FE")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF2FF")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return [
        title,
        Spacer(1, 0.20 * inch),
        content,
        Spacer(1, 0.30 * inch),
    ]


def section_generation_and_consumption_overview(
    *, doc, styles, generation_hourly, consumption_hourly
):
    """Create generation and consumption overview section.

    Args:
        doc: Document template.
        styles: Style dictionary.
        generation_hourly: DataFrame with generation hourly data.
        consumption_hourly: DataFrame with consumption hourly data.
    """
    title = Paragraph(
        "<para align='center'>Generation & Consumption Overview</para>",
        styles["h2_center"],
    )
    section_elements = [
        title,
        Spacer(1, 0.12 * inch),
    ]

    def build_table(label: str, df: pd.DataFrame | None, *, highlight: str):
        heading = Paragraph(f"<b>{label}</b>", styles["body_center"])
        if df is None or df.empty:
            return [
                heading,
                Spacer(1, 0.05 * inch),
                Paragraph("No data available.", styles["body_center"]),
                Spacer(1, 0.15 * inch),
            ]

        df_sorted = df.sort_index()
        columns = list(df_sorted.columns)
        numeric_block = df_sorted[columns].to_numpy(dtype=float, copy=True)
        numeric_vals = numeric_block[~np.isnan(numeric_block)]
        min_val = float(np.nanmin(numeric_vals)) if numeric_vals.size else None
        max_val = float(np.nanmax(numeric_vals)) if numeric_vals.size else None

        if highlight == "green":
            target_rgb = (0.72, 0.9, 0.72)
        else:
            target_rgb = (0.96, 0.75, 0.75)

        def format_col(*, col_val):
            try:
                col_int = int(col_val)
            except (TypeError, ValueError):
                return str(col_val)
            return f"{col_int:02d}:00"

        def format_idx(*, idx_val):
            if isinstance(idx_val, (datetime.datetime, datetime.date)):
                return pd.Timestamp(idx_val).strftime("%b %d")
            return str(idx_val)

        def format_val(*, raw_val):
            if pd.isna(raw_val):
                return "—"
            return f"{raw_val:.2f}"

        table_data = [
            ["Date"] + [format_col(col_val=col) for col in columns],
        ]
        for idx_val, row in df_sorted.iterrows():
            row_values = [format_val(raw_val=row[col]) for col in columns]
            table_data.append([format_idx(idx_val=idx_val)] + row_values)

        col_count = len(table_data[0])
        col_width = doc.width / col_count if col_count else doc.width
        tbl = Table(
            table_data,
            colWidths=[col_width] * col_count,
            hAlign="CENTER",
        )
        tbl.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("ALIGN", (0, 1), (0, -1), "LEFT"),
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 6),
                    ("FONT", (0, 1), (-1, -1), "Helvetica", 6),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 1.5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 1.5),
                    ("TOPPADDING", (0, 0), (-1, -1), 0.8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0.8),
                ]
            )
        )

        if min_val is not None and max_val is not None:
            span = max(max_val - min_val, 1e-9)

            def compute_color(*, val: float):
                if pd.isna(val):
                    return None
                frac = (val - min_val) / span if span else 1.0
                frac = max(0.0, min(frac, 1.0))
                r = 1 - frac * (1 - target_rgb[0])
                g = 1 - frac * (1 - target_rgb[1])
                b = 1 - frac * (1 - target_rgb[2])
                return colors.Color(r, g, b)

            style_updates = []
            for row_idx, idx_val in enumerate(df_sorted.index, start=1):
                for col_idx, col in enumerate(columns, start=1):
                    raw_value = df_sorted.at[idx_val, col]
                    numeric_value = float(pd.to_numeric(raw_value, errors="coerce"))
                    color = compute_color(val=numeric_value)
                    if color is not None:
                        style_updates.append(
                            (
                                "BACKGROUND",
                                (col_idx, row_idx),
                                (col_idx, row_idx),
                                color,
                            )
                        )
            if style_updates:
                tbl.setStyle(TableStyle(style_updates))

        return [
            heading,
            Spacer(1, 0.05 * inch),
            tbl,
            Spacer(1, 0.18 * inch),
        ]

    section_elements.extend(
        build_table(
            "Generation (MWh)",
            generation_hourly,
            highlight="green",
        )
    )
    section_elements.extend(
        build_table(
            "Consumption (MWh)",
            consumption_hourly,
            highlight="red",
        )
    )
    section_elements.append(PageBreak())
    return section_elements


# ---------------------------------------------------------------------------
# Build report
# ---------------------------------------------------------------------------


async def build_report(
    *,
    filename: str,
    project: models.Project,
    request: BESSMonthlyReportRequest,
    kpi_sums: dict[int, float],
    kpi_means: dict[int, float],
    soc_stats: dict[str, float],
    rev_breakdown_by_type_bytes: bytes | None = None,
    rev_breakdown_df: pd.DataFrame | None = None,
    bess_pcs_availability_bytes: bytes | None = None,
    event_summary_metrics: dict[str, float] | None = None,
    kpi_expected_values: dict[str, float] | None = None,
    executive_summary_df: pd.DataFrame | None = None,
    generation_hourly: pd.DataFrame | None = None,
    consumption_hourly: pd.DataFrame | None = None,
    event_table: pd.DataFrame | None = None,
    monthly_tbx: dict[str, float] | None = None,
    current_soh: float | None = None,
):
    """Build and save the complete PDF report.

    Args:
        filename: Output name of the report file.
        project: Project model instance.
        request: Report request with month, strategies, and commentary.
        kpi_sums: Dictionary of KPI sums by type ID.
        kpi_means: Dictionary of KPI means by type ID.
        soc_stats: Dictionary with soc_min and soc_max.
        rev_breakdown_by_type_bytes: Optional revenue breakdown chart bytes.
        rev_breakdown_df: Optional revenue breakdown DataFrame.
        bess_pcs_availability_bytes: Optional availability chart bytes.
        event_summary_metrics: Optional event summary metrics.
        kpi_expected_values: Optional expected KPI values.
        executive_summary_df: Optional executive summary DataFrame.
        generation_hourly: Optional generation pivot DataFrame.
        consumption_hourly: Optional consumption pivot DataFrame.
        event_table: Optional DataFrame with detailed event loss data.
        monthly_tbx: Optional dictionary of TBX values.
        current_soh: Optional current SOH.
    """
    styles = build_styles()

    doc = BaseDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        title=os.path.basename(filename),
    )
    doc.title = os.path.basename(filename)

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates(
        PageTemplate(
            id="content",
            frames=[frame],
            onPage=draw_header_footer,
        )
    )

    elements = []
    # 1) Project details
    elements.extend(await section_project_details(doc=doc, project=project))

    # 2) Commentary
    if request.operational_commentary is not None:
        elements += section_operational_commentary(
            styles=styles, commentary=request.operational_commentary
        )
    else:
        elements += section_operational_commentary(styles=styles, commentary="")

    # 3) Strategy table + image
    elements += section_strategy_table_with_image(
        doc=doc, styles=styles, strategies=request.strategies, month=request.month
    )

    # 4) Revenue Breakdown by Type (bytes provided by caller)
    if rev_breakdown_by_type_bytes is not None:
        if rev_breakdown_df is not None:
            elements += section_revenue_breakdown_with_table(
                doc=doc,
                img_bytes_or_path=rev_breakdown_by_type_bytes,
                rev_breakdown_df=rev_breakdown_df,
                styles=styles,
            )
        else:
            elements += section_full_width_image(
                doc=doc, img_bytes_or_path=rev_breakdown_by_type_bytes, styles=styles
            )
    elements.append(PageBreak())

    # 5) BESS SOC + SmartBidder Metrics
    elements += section_two_column_metrics(
        doc=doc,
        styles=styles,
        kpi_sums=kpi_sums,
        kpi_means=kpi_means,
        soc_stats=soc_stats,
        kpi_expected_values=kpi_expected_values,
        request=request,
        current_soh=current_soh,
    )

    # 6) Monthly Comparison
    if executive_summary_df is not None:
        elements += section_monthly_comparison(
            doc=doc, styles=styles, executive_summary_df=executive_summary_df
        )
    else:
        elements += section_monthly_comparison(
            doc=doc, styles=styles, executive_summary_df=pd.DataFrame()
        )

    # 7) TBX Comparison
    if monthly_tbx is not None:
        elements += section_tbx_comparison(
            doc=doc, styles=styles, monthly_tbx=monthly_tbx
        )
    else:
        elements += section_tbx_comparison(doc=doc, styles=styles, monthly_tbx={})

    # 7) Executive KPI Index
    # elements += section_full_width_image(doc, radar_png, styles)
    elements.append(PageBreak())

    # 8) Generation and Consumption Overview
    elements += section_generation_and_consumption_overview(
        doc=doc,
        styles=styles,
        generation_hourly=generation_hourly,
        consumption_hourly=consumption_hourly,
    )

    # 7) Events overview (requires bytes + rows)
    if bess_pcs_availability_bytes is not None:
        if event_summary_metrics is not None:
            rollup = [[k, v] for k, v in event_summary_metrics.items()]
        else:
            rollup = []
        elements += section_events_overview(
            doc=doc,
            styles=styles,
            image_bytes=bess_pcs_availability_bytes,
            rollup_rows=rollup,
            event_table=event_table,
        )
    else:
        elements += section_no_events_overview(doc=doc, styles=styles)

    doc.build(elements)


# ---------------------------------------------------------------------------
# TPS Data
# ---------------------------------------------------------------------------


def pivot_to_daily_hourly(
    *,
    s: pd.Series,
):
    """Create a day/hour pivoted DataFrame from a time-indexed series.

    Args:
        s: Series with a DatetimeIndex representing interval values.

    Returns:
        DataFrame indexed by day with columns for each hour (0-23).
    """
    datetime_index = pd.to_datetime(s.index, errors="coerce")

    tmp = s.rename("value").to_frame()
    tmp = tmp.assign(
        day=datetime_index.date,
        hour=datetime_index.hour,
    )

    daily_hourly = tmp.drop_duplicates(subset=["day", "hour"]).pivot(
        index="day",
        columns="hour",
        values="value",
    )
    return daily_hourly


async def get_tps_data(
    *,
    project: models.Project,
    parent_element_identifier: str,
    start: datetime.datetime,
    end: datetime.datetime,
    token: str,
):
    """Fetch TPS (Third-Party Settlement) data from API.

    Args:
        project: Project model instance.
        parent_element_identifier: TPS element identifier.
        start: Start datetime.
        end: End datetime.
        token: API authentication token.

    Returns:
        Tuple containing:
            - Daily summed DataFrame.
            - TPS element display name.
            - Generation hourly pivot DataFrame.
            - Consumption hourly pivot DataFrame.

    Note:
        Uses blocking HTTP requests. Consider using httpx for async requests.
    """
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://api.ptp.energy/v1/markets/ERCOTNodal/endpoints/Battery-Settlement-Details"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            response_meta = await response.json()
    identifiers = [
        x["identifier"]
        for x in response_meta["data"]["elements"]
        if (
            x["parentElementIdentifier"] == parent_element_identifier
            or x["identifier"] == parent_element_identifier
        )
    ]
    tps_name = [
        x
        for x in response_meta["data"]["elements"]
        if x["identifier"] == parent_element_identifier
    ][0]["name"]
    df = pd.DataFrame()

    start_zoned = datetime.datetime.combine(
        start, datetime.time.min, tzinfo=ZoneInfo(project.time_zone)
    ).isoformat()
    end_zoned = datetime.datetime.combine(
        end, datetime.time.min, tzinfo=ZoneInfo(project.time_zone)
    ).isoformat()

    for element in identifiers:
        params = {
            "begin": start_zoned,
            "end": end_zoned,
            "elements": [element],
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{url}/data", headers=headers, params=params
            ) as response:
                response_data = await response.json()

        data_points = response_data.get("data", [])
        if not data_points:
            continue

        data = data_points[0]
        element_name = data["element"]

        df_element = pd.DataFrame()

        for dp in data["dataPoints"]:
            temp = pd.DataFrame(dp["values"])

            temp["intervalStartUtc"] = pd.to_datetime(
                temp["intervalStartUtc"], utc=True
            )
            temp["intervalEndUtc"] = pd.to_datetime(temp["intervalEndUtc"], utc=True)

            # assumes temp["data"] is like [{"value": "..."}] and you want the first one
            temp["data"] = temp["data"].map(lambda x: float(x[0]["value"]))

            temp = temp.set_index("intervalStartUtc").drop(columns=["intervalEndUtc"])

            key_name = dp["keyName"]

            # Make a 2-level MultiIndex column: (element, keyName)
            temp.columns = pd.MultiIndex.from_tuples(
                [(element_name, key_name)],
                names=["element", "keyName"],
            )

            df_element = pd.concat([df_element, temp], axis=1)

        df = pd.concat([df, df_element], axis=1)

    if df.empty:
        return (
            pd.DataFrame(),
            tps_name,
            pd.DataFrame(),
            pd.DataFrame(),
        )

    localized_index = pd.to_datetime(df.index, utc=True)
    localized_index = localized_index.tz_convert(project.time_zone)
    df.index = localized_index
    df.index.name = "intervalStartLocal"
    generation_series = df.get((tps_name, "RT_Generation_Qty"))
    consumption_series = df.get((tps_name, "RT_Consumption_Qty"))

    if generation_series is not None:
        generation_hourly = pivot_to_daily_hourly(s=generation_series)
    else:
        generation_hourly = pd.DataFrame()

    if consumption_series is not None:
        consumption_hourly = pivot_to_daily_hourly(s=consumption_series)
    else:
        consumption_hourly = pd.DataFrame()

    daily_index = localized_index.normalize()
    df_sums = df.groupby(daily_index).sum()
    df_sums.index = [idx.date() for idx in df_sums.index]

    return df_sums, tps_name, generation_hourly, consumption_hourly


async def generate_tps_metrics(
    *,
    tps_data: pd.DataFrame,
    tps_name: str,
):
    """Generate revenue breakdown chart and metrics from TPS data.

    Args:
        tps_data: DataFrame with TPS settlement data.
        tps_name: Name of the TPS element.

    Returns:
        Tuple of (chart_bytes, report_df, other_metrics_dict).
    """
    df_report = pd.DataFrame(index=tps_data.index)
    element_frame = tps_data.get(tps_name, pd.DataFrame())

    def _safe_series(column_name: str) -> pd.Series:
        column = element_frame.get(column_name)
        if column is None:
            return pd.Series(0, index=tps_data.index)
        return column

    df_report["Real-Time Energy"] = _safe_series("RT_Energy_Amt")
    df_report["Day-Ahead Energy"] = _safe_series("DA_Energy_Amt")

    ancillary_columns = [
        "DA_ECRS_Amt",
        "DA_RRS_Amt",
        "DA_NS_Amt",
        "DA_Reg_Down_Amt",
        "DA_Reg_Up_Amt",
    ]
    df_report["Ancillary Services"] = pd.DataFrame(
        {col: _safe_series(col) for col in ancillary_columns}
    ).sum(axis=1)

    misc_columns = ["BP_Dev_Amt", "RT_Reliability_Deployment_Imbalance_Amt"]
    df_report["Misc Charges"] = pd.DataFrame(
        {col: _safe_series(col) for col in misc_columns}
    ).sum(axis=1)
    df_report["Net Profit"] = df_report.sum(axis=1)

    # Separate columns (excluding Net Profit for bars)
    bar_columns = [col for col in df_report.columns if col != "Net Profit"]

    # Create chart using utility function
    fig = create_stacked_bar_chart(
        df=df_report,
        bar_columns=bar_columns,
        line_column="Net Profit",
        title="Revenue Breakdown by Type",
        xaxis_tickformat="%b %d, %Y",
        yaxis_format="$,.0f",
    )

    rev_breakdown_by_type_bytes = fig.to_image(format="png")
    rev_breakdown_df = df_report.reset_index(drop=False)
    other_tps_data = {
        "Total Delivered Energy": (
            _safe_series("RT_Generation_Qty") - _safe_series("RT_Consumption_Qty")
        ).sum()
    }
    return rev_breakdown_by_type_bytes, rev_breakdown_df, other_tps_data


async def get_tbx(
    *,
    project: models.Project,
    start: datetime.datetime,
    end: datetime.datetime,
    token: str,
    total_profit: float,
):
    """Get TB-1, TB-2, and TB-4 data for a project.

    Args:
        project: Project model instance.
        start: Start datetime.
        end: End datetime.
        token: API authentication token.
        total_profit: Total profit from TPS data.

    Returns:
        TBX data DataFrame.
    """
    headers = {"Authorization": f"Bearer {token}"}
    base_url = "https://api.ptp.energy/warehouse-data/ERCOTRealtimeLMP"
    node = project.interconnecting_substation
    raw_params = {
        "intervalEndingUtcRangeBegin": pd.Timestamp(start)
        .tz_localize(project.time_zone)
        .tz_convert("UTC")
        .tz_convert(None)
        .isoformat(),
        "intervalEndingUtcRangeEnd": pd.Timestamp(end)
        .tz_localize(project.time_zone)
        .tz_convert("UTC")
        .tz_convert(None)
        .isoformat(),
        "settlementPointFilter": node,
    }
    params: dict[str, str] = {k: v for k, v in raw_params.items() if v is not None}
    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, headers=headers, params=params) as response:
            response_data = await response.json()
    df = pd.DataFrame(response_data)
    df["intervalEndingUtc"] = pd.to_datetime(df["intervalEndingUtc"])
    df["intervalEndingUtc"] = df["intervalEndingUtc"].dt.tz_convert(project.time_zone)
    df = df.rename(columns={"intervalEndingUtc": "intervalEndingLocal"})

    work = df[["intervalEndingLocal", "value"]].copy()
    work["date"] = work["intervalEndingLocal"].dt.date
    work["hour"] = work["intervalEndingLocal"].dt.hour
    grouped = work.groupby(["date", "hour"])["value"].mean()
    daily_tbx = pd.DataFrame()
    for x in [1, 2, 4]:
        for date in work["date"].unique():
            arr = grouped.loc[date].to_numpy()
            arr.sort()
            bottom = arr[:x].sum()
            top = arr[-x:].sum()
            tbx = (top - bottom) / 1000
            daily_tbx.loc[date, f"{x}"] = tbx
    daily_tbx.index = pd.to_datetime(daily_tbx.index)
    daily_tbx = daily_tbx.sort_index()
    monthly_tbx = daily_tbx.groupby(pd.Grouper(freq="ME")).sum()
    monthly_records = monthly_tbx.to_dict(orient="records")
    if not monthly_records:
        return {
            "1": 0.0,
            "2": 0.0,
            "4": 0.0,
            "realized_intraday_value": 0.0,
        }
    tbx_dict = monthly_records[0]
    if project.poi is None or project.poi == 0:
        tbx_dict["realized_intraday_value"] = 0
    tbx_dict["realized_intraday_value"] = total_profit / project.poi / 1000
    return tbx_dict


# ---------------------------------------------------------------------------
# Proximal Data
# ---------------------------------------------------------------------------


async def get_tps_element_identifier(
    *,
    project: models.Project,
    db: AsyncSession,
) -> str:
    """Get TPS element identifier for a project.

    Args:
        project: Project model instance.
        db: Async database session.

    Returns:
        TPS element identifier string.

    Raises:
        KeyError: If project name_short is not in the mapping.
    """
    qse_integration = await crud_get_qse_integration_by_project_id(
        db=db,
        project_id=project.project_id,
    )
    if qse_integration is None:
        raise KeyError("QSE integration not found")
    if qse_integration.qse_project_identifier is None:
        raise KeyError("QSE project identifier not configured")
    return cast(str, qse_integration.qse_project_identifier)


async def yearly_degradation_rate_from_soh(
    *,
    kpi_type_id: int,
    start: datetime.date,
    end: datetime.date,
    project: models.Project,
    date_col: str = "date",
    soh_col: str = "project_data",
    min_span_days: int = 30,
    atol: float = 1e-9,
) -> dict:
    """
    Returns yearly degradation rate based on linear regression of SoH (%) vs time
    (years). If SoH is constant (within tolerance) or regression is ill-posed,
    returns 0%/yr.

    Returns dict with:
      degradation_rate_pct_per_year, slope_pct_per_year, r2, stderr, n_points, span_days
    """
    kpi_data_query = crud_get_kpi_data(
        start=start.replace(month=1, day=1),
        end=end,
        project_ids=[project.project_id],
        kpi_type_ids=[kpi_type_id],
        include_device_data=False,
    )
    kpi_df = await kpi_data_query.get_async(output_type=OutputType.PANDAS)
    soh_df = kpi_df.dropna(subset=[soh_col, date_col])

    if soh_df.empty:
        return {
            "degradation_rate_pct_per_year": 0.0,
            "slope_pct_per_year": 0.0,
            "r2": np.nan,
            "stderr": np.nan,
            "n_points": 0,
            "span_days": 0,
        }

    soh_df[date_col] = pd.to_datetime(soh_df[date_col], utc=True, errors="coerce")
    soh_df = soh_df.dropna(subset=[date_col]).sort_values(date_col)

    soh = soh_df[soh_col].astype(float).to_numpy()
    dates = soh_df[date_col]

    n = soh.size
    span_days = int((dates.max() - dates.min()).total_seconds() // 86400)

    # Not enough points or not enough time span → cannot infer a meaningful yearly rate
    if n < 2 or span_days < min_span_days:
        return {
            "degradation_rate_pct_per_year": 0.0,
            "slope_pct_per_year": 0.0,
            "r2": np.nan,
            "stderr": np.nan,
            "n_points": int(n),
            "span_days": span_days,
        }

    # If SoH is constant (or effectively constant), define degradation as 0
    if np.allclose(soh, soh[0], atol=atol, rtol=0.0):
        return {
            "degradation_rate_pct_per_year": 0.0,
            "slope_pct_per_year": 0.0,
            "r2": 1.0,  # perfectly “fits” a flat line
            "stderr": 0.0,
            "n_points": int(n),
            "span_days": span_days,
        }

    # Build x as "years since first sample" for each row
    t0 = dates.iloc[0]
    years = (dates - t0).dt.total_seconds().to_numpy() / (365.25 * 24 * 3600)

    # Guard: if timestamps are identical (shouldn’t happen if
    # span_days check passed, but safe)
    if np.allclose(years, years[0], atol=0.0, rtol=0.0):
        return {
            "degradation_rate_pct_per_year": 0.0,
            "slope_pct_per_year": 0.0,
            "r2": np.nan,
            "stderr": np.nan,
            "n_points": int(n),
            "span_days": span_days,
        }

    result = linregress(years, soh)
    slope = float(result.slope)  # % per year (likely negative)
    degradation_rate = float(-slope)  # positive %/yr when declining
    r2 = float(result.rvalue**2)
    stderr = float(result.stderr) if result.stderr is not None else np.nan

    return {
        "degradation_rate_pct_per_year": degradation_rate,
        "slope_pct_per_year": slope,
        "r2": r2,
        "stderr": stderr,
        "n_points": int(n),
        "span_days": span_days,
    }


async def get_kpi_data(
    *,
    project: models.Project,
    project_db_sync: Session,
    start: datetime.date,
    end: datetime.date,
):
    """Fetch KPI data and SOC statistics for the report period.

    Args:
        project: Project model instance.
        db: Async database session.
        project_db_sync: Synchronous database session.
        start: Start date.
        end: End date.

    Returns:
        Tuple of (kpi_sums, kpi_means, soc_stats).
    """
    kpi_type_ids = [
        KPIType.BESS_STRING_CYCLE_COUNT.value,
        KPIType.BESS_STRING_SOH.value,
        KPIType.BESS_STRING_RESTING_SOC_PERCENT.value,
        KPIType.PROJECT_AVERAGE_SOC_PERCENT.value,
    ]
    kpi_data_query = crud_get_kpi_data(
        start=start,
        end=end,
        project_ids=[project.project_id],
        kpi_type_ids=kpi_type_ids,
        include_device_data=False,
    )
    kpi_df = await kpi_data_query.get_async(
        output_type=OutputType.PANDAS,
    )

    # TODO: Remove the explicit tag_id and find dynamically instead.
    # This should query for the PROJECT_SOC_PERCENT sensor type tag
    tag_id = 217648
    project_soc_data_instance = DataTimeseries(
        project_db=project_db_sync,
        project_name_short=project.name_short,
        # sensor_type_ids=[core.enumerations.SensorType.PROJECT_SOC_PERCENT.value],
        filter_method=FilterMethod.TAG_IDS,
        filter_values=[tag_id],
        query_start=pd.Timestamp(start),
        query_end=pd.Timestamp(end),
        freq=TimeInterval.ONE_MINUTE,
        ensure_full_range=True,
    )
    project_soc_data = await project_soc_data_instance.get()
    soc_df = project_soc_data.df.to_pandas()
    soc_df = soc_df.set_index("time", drop=True)
    soc_df.index = pd.to_datetime(soc_df.index)
    soc_df.columns = soc_df.columns.astype(int)
    stats = {"soc_min": soc_df[tag_id].min(), "soc_max": soc_df[tag_id].max()}
    sums = kpi_df[["kpi_type_id", "project_data"]].groupby("kpi_type_id").sum()
    means = kpi_df[["kpi_type_id", "project_data"]].groupby("kpi_type_id").mean()

    degradation = await yearly_degradation_rate_from_soh(
        kpi_type_id=KPIType.BESS_STRING_SOH,
        start=start,
        end=end,
        project=project,
    )

    return sums, means, stats, degradation["degradation_rate_pct_per_year"]


async def build_event_data(
    *,
    project_db: AsyncSession,
    project: models.Project,
    start: datetime.date,
    end: datetime.date,
):
    """Build event data including availability chart and summary metrics.

    Args:
        project_db: Async database session.
        project: Project model instance.
        start: Start date.
        end: End date.

    Returns:
        Tuple of (availability_chart_bytes, event_summary_metrics_dict).
    """
    capacity_loss_kwh_query = crud_project_events.get_windowed_capacity_loss_kwh_async(
        start=pd.Timestamp(start),
        end=pd.Timestamp(end),
    )
    capacity_loss_kwh = await capacity_loss_kwh_query.get_async(
        schema=project.name_short, output_type=OutputType.PANDAS
    )
    event_data_query = crud_project_events.get_windowed_events(
        start=pd.Timestamp(start),
        end=pd.Timestamp(end),
    )
    event_df = await event_data_query.get_async(
        schema=project.name_short,
        output_type=OutputType.PANDAS,
    )
    if event_df is None or event_df.empty:
        return None, None, 0.0, None
    ## Convert capacity loss kWh to MWh
    cap_loss_mwh_df = capacity_loss_kwh.assign(
        capacity_loss_mwh=lambda x: x["capacity_loss_kwh"] / 1_000
    ).drop(columns="capacity_loss_kwh")

    def _to_naive_timestamp(value):  # nosemgrep: python-enforce-keyword-only-args
        ts = pd.Timestamp(value)
        if ts.tz is not None:
            return ts.tz_localize(None)
        return ts

    cap_loss_by_event = (
        cap_loss_mwh_df.groupby("event_id")["capacity_loss_mwh"].sum()
        if not cap_loss_mwh_df.empty
        else pd.Series(dtype="float64")
    )
    event_device_type_map = (
        cap_loss_mwh_df.groupby("event_id")["device_type_id"].first().to_dict()
        if not cap_loss_mwh_df.empty
        else {}
    )

    event_df["time_start"] = event_df["time_start"].apply(_to_naive_timestamp)
    event_df["time_end"] = event_df["time_end"].apply(
        lambda value: _to_naive_timestamp(value) if pd.notna(value) else pd.NaT
    )

    metrics_df = event_df.copy()
    clip_start = _to_naive_timestamp(start)
    clip_end = _to_naive_timestamp(end)
    metrics_df["overlap_start"] = metrics_df["time_start"].clip(
        lower=clip_start,
        upper=clip_end,
    )
    metrics_df["overlap_end"] = (
        metrics_df["time_end"].fillna(clip_end).clip(lower=clip_start, upper=clip_end)
    )
    metrics_df = metrics_df[
        metrics_df["overlap_start"] < metrics_df["overlap_end"]
    ].copy()
    metrics_df["overlap_hours"] = (
        metrics_df["overlap_end"] - metrics_df["overlap_start"]
    ).dt.total_seconds() / 3600
    metrics_df["capacity_loss_mwh"] = (
        metrics_df["event_id"].map(cap_loss_by_event).fillna(0.0)
    )
    if event_device_type_map:
        metrics_df["device_type_id"] = metrics_df["event_id"].map(event_device_type_map)
    else:
        metrics_df["device_type_id"] = pd.NA

    metrics_columns = [
        "event_id",
        "device_id",
        "device_type_id",
        "overlap_hours",
        "capacity_loss_mwh",
        "time_start",
        "time_end",
        "failure_mode_id",
    ]
    if metrics_df.empty:
        top_ten_losses = pd.DataFrame(columns=metrics_columns)
    else:
        top_ten_losses = (
            metrics_df.sort_values("overlap_hours", ascending=False)
            .loc[:, metrics_columns]
            .head(10)
            .reset_index(drop=True)
        )

    loss_by_failure_mode_id = cap_loss_mwh_df.groupby("failure_mode_id").agg(
        {"capacity_loss_mwh": "sum"}
    )
    loss_by_failure_mode_id = loss_by_failure_mode_id.reset_index(drop=False)

    failure_mode_ids = (
        loss_by_failure_mode_id["failure_mode_id"].dropna().unique().tolist()
        if not loss_by_failure_mode_id.empty
        else []
    )
    if failure_mode_ids:
        failure_modes_query = crud_get_failure_modes(
            failure_mode_ids=failure_mode_ids,
        )
        failure_modes = await failure_modes_query.get_async(
            output_type=OutputType.PANDAS,
        )
        failure_mode_lookup = failure_modes.set_index("failure_mode_id")[
            "name_long"
        ].to_dict()
    else:
        failure_mode_lookup = {}

    loss_by_failure_mode_id["failure_mode_name_long"] = (
        loss_by_failure_mode_id["failure_mode_id"]
        .map(failure_mode_lookup)
        .fillna("Unknown Failure Mode")
    )

    if not top_ten_losses.empty:
        top_ten_losses["failure_mode_name_long"] = (
            top_ten_losses["failure_mode_id"]
            .map(failure_mode_lookup)
            .fillna("Unknown Failure Mode")
        )
        top_ten_losses["financial_loss"] = (
            top_ten_losses["capacity_loss_mwh"] * ERCOT_LOSS_PER_DAY * 1_000 / 24
        )

    all_devices = await crud_get_project_devices_async(
        db=project_db, device_type_ids=[DeviceType.BESS_PCS_MODULE]
    )
    total_ac_power_capacity = float(sum(x.capacity_ac for x in all_devices))
    total_energy_capacity = (
        total_ac_power_capacity * (end - start).total_seconds() / 3600 / 1_000
    )

    losses_dict = (
        loss_by_failure_mode_id.set_index("failure_mode_name_long")["capacity_loss_mwh"]
        .sort_values(ascending=False)
        .mul(-1.0)
        .to_dict()
        if not loss_by_failure_mode_id.empty
        else {}
    )

    fig = create_waterfall_chart(
        total_capacity=total_energy_capacity,
        losses=losses_dict,
        title="Capacity Impact by Failure Mode",
        xaxis_title="",
        yaxis_title="Capacity (MWh)",
        yaxis_format=",.2f",
    )
    bess_pcs_availability_bytes = fig.to_image(format="png")
    frac_covered = covered_fraction_by_any_event(event_df, start, end)
    lost_capacity_mwh = cap_loss_mwh_df["capacity_loss_mwh"].sum()
    event_summary_metrics = {
        "Total Unavailable Capacity": f"{lost_capacity_mwh:,.2f} MWh",
        "Total Financial Impact": (
            f"${lost_capacity_mwh * ERCOT_LOSS_PER_DAY * 1_000 / 24:,.2f}*"
        ),
        "Total Events": len(cap_loss_mwh_df),
        "% of Time with Events": f"{frac_covered:.2%}",
    }
    return (
        bess_pcs_availability_bytes,
        event_summary_metrics,
        lost_capacity_mwh,
        top_ten_losses,
    )


async def build_event_table(
    *,
    project_db: AsyncSession,
    top_ten_losses: pd.DataFrame,
):
    """Build event table."""
    if top_ten_losses.empty:
        return pd.DataFrame(
            columns=[
                "Device Name",
                "Failure Mode",
                "Start Time",
                "End Time",
                "Financial Loss ($)",
            ]
        )
    devices = await crud_get_project_devices_async(
        db=project_db,
        device_ids=top_ten_losses["device_id"].unique().tolist(),
        deep=True,
    )
    device_to_name = {
        x.device_id: f"{x.device_type.name_long} {x.name_long}" for x in devices
    }
    top_ten_losses["name_long"] = top_ten_losses["device_id"].map(device_to_name)
    if "failure_mode_name_long" not in top_ten_losses.columns:
        top_ten_losses["failure_mode_name_long"] = "Unknown Failure Mode"
    if "financial_loss" not in top_ten_losses.columns:
        top_ten_losses["financial_loss"] = (
            top_ten_losses["capacity_loss_mwh"] * ERCOT_LOSS_PER_DAY * 1_000 / 24
        )
    event_table = top_ten_losses[
        [
            "name_long",
            "failure_mode_name_long",
            "time_start",
            "time_end",
            "financial_loss",
        ]
    ]
    event_table = event_table.sort_values(
        ["financial_loss", "name_long"], ascending=[False, True]
    )
    event_table.columns = [
        "Device Name",
        "Failure Mode",
        "Start Time",
        "End Time",
        "Financial Loss ($)",
    ]

    return event_table


async def generate_executive_summary(
    *,
    other_tps_data: dict[str, float],
    rev_breakdown_df: pd.DataFrame,
    expected_values: dict[str, float] | None = None,
    total_availability: float,
    capacity_factor: float,
    degradation_rate: float,
    deg_rate_expected: float,
    request: BESSMonthlyReportRequest,
):
    """Generate executive summary DataFrame with actual vs expected metrics.

    Args:
        other_tps_data: Dictionary with additional TPS metrics.
        rev_breakdown_df: DataFrame with revenue breakdown data.
        expected_values: Optional dictionary of expected values. If None,
            uses hardcoded defaults (should be replaced with real data).
        total_availability: Total availability.
        capacity_factor: Capacity factor.
        degradation_rate: Degradation rate.
        deg_rate_expected: Expected degradation rate.
        request: Request data including month, strategies, and commentary.

    Returns:
        DataFrame with metrics and deltas.
    """
    # TODO: Replace hardcoded expected values with real data source
    defaults = {
        "total_revenue": 0,
        "total_energy_delivered": 0,
        "average_capacity_factor": 0.25,
        "capacity_weighted_availability": 0.98,
        "degradation_rate": 0.0040,
        "forecast_accuracy": 0.80,
    }
    if expected_values:
        defaults.update(expected_values)

    active_strategy = next(
        (s for s in request.strategies if s.name == "Active Strategy"), None
    )
    perfect_foresight_strategy = next(
        (s for s in request.strategies if s.name == "Perfect Foresight"), None
    )

    # Category: (actual, expected, delta)
    executive_summary_df = pd.DataFrame(
        index=[
            "Total Revenue",
            "Total Energy Delivered",
            "Average Capacity Factor",
            "Capacity-Weighted Availability",
            "Degradation Rate",
            "Forecast Accuracy",
        ],
        columns=["This Month", "Expected", "Delta"],
    )

    executive_summary_df.loc["Total Revenue", "This Month"] = rev_breakdown_df[
        "Net Profit"
    ].sum()
    executive_summary_df.loc["Total Revenue", "Expected"] = defaults["total_revenue"]
    executive_summary_df.loc["Total Energy Delivered", "This Month"] = other_tps_data[
        "Total Delivered Energy"
    ]
    executive_summary_df.loc["Total Energy Delivered", "Expected"] = defaults[
        "total_energy_delivered"
    ]
    # TODO: Replace hardcoded actual values with real calculations
    executive_summary_df.loc["Average Capacity Factor", "This Month"] = capacity_factor
    executive_summary_df.loc["Average Capacity Factor", "Expected"] = defaults[
        "average_capacity_factor"
    ]
    executive_summary_df.loc["Capacity-Weighted Availability", "This Month"] = (
        total_availability
    )
    executive_summary_df.loc["Capacity-Weighted Availability", "Expected"] = defaults[
        "capacity_weighted_availability"
    ]
    executive_summary_df.loc["Degradation Rate", "This Month"] = degradation_rate
    executive_summary_df.loc["Degradation Rate", "Expected"] = deg_rate_expected
    active_month_value = (
        active_strategy.month_value
        if active_strategy and active_strategy.month_value is not None
        else None
    )
    perfect_month_value = (
        perfect_foresight_strategy.month_value
        if (
            perfect_foresight_strategy
            and perfect_foresight_strategy.month_value is not None
            and perfect_foresight_strategy.month_value != 0
        )
        else None
    )
    executive_summary_df.loc["Forecast Accuracy", "This Month"] = (
        active_month_value / perfect_month_value
        if active_month_value is not None and perfect_month_value is not None
        else None
    )
    executive_summary_df.loc["Forecast Accuracy", "Expected"] = defaults[
        "forecast_accuracy"
    ]
    executive_summary_df.loc[:, "Delta"] = executive_summary_df.apply(
        lambda x: calc_delta_percentage(
            actual=x["This Month"], expected=x["Expected"], format_as_change=True
        ),
        axis=1,
    )
    return executive_summary_df


def compare_to_perfect_foresight(*, strategies: list[BESSMonthlyReportStrategy]):
    """Compare the strategies to the perfect foresight strategy."""
    pf_value = None
    for strategy in strategies:
        if strategy.name == "Perfect Foresight":
            pf_value = strategy.month_value
            break

    if not pf_value:
        for strategy in strategies:
            strategy.vs_perfect = None
    else:
        inv_pf_value = 1 / pf_value
        for strategy in strategies:
            strategy.vs_perfect = (
                None
                if strategy.month_value is None
                else strategy.month_value * inv_pf_value
            )
    return strategies


async def get_contract_uec(
    *,
    project: models.Project,
):
    """Get the contract UEC for the project.
    Args:
        project: Project model instance.

    Returns:
        DataFrame with the contract UEC.
    """
    contract_kpis_query = crud_get_contract_kpis(project_ids=[project.project_id])
    contract_kpis = await contract_kpis_query.get_async(output_type=OutputType.PANDAS)
    if contract_kpis.empty:
        return pd.DataFrame(columns=["uec"])
    contract_uec = contract_kpis[
        contract_kpis["kpi_type_id"] == KPIType.BESS_DC_ENCLOSURE_USABLE_ENERGY_CAPACITY
    ].iloc[0]

    threshold = contract_uec.get("threshold")
    if not threshold or "values" not in threshold:
        return pd.DataFrame(columns=["uec"])

    threshold_values = threshold["values"]
    if not threshold_values:
        return pd.DataFrame(columns=["uec"])

    contract_uec_df = pd.DataFrame(
        index=threshold_values.keys(),
        data=threshold_values.values(),
        columns=["uec"],
    )
    contract_uec_df.index = pd.to_datetime(contract_uec_df.index)
    contract_uec_df = contract_uec_df.sort_index()
    return contract_uec_df


def degradation_rate_from_contract_uec(
    *,
    contract_uec: pd.DataFrame,
    start: pd.Timestamp,
):
    """Get the degradation rate from the contract UEC.
    Args:
        contract_uec: DataFrame with the contract UEC.
        start: Start date.
        end: End date.

    Returns:
        Degradation rate.
    """
    if contract_uec.empty:
        return 0.0

    current_aniv = contract_uec.index.asof(start)
    if pd.isna(current_aniv):
        year_slice = contract_uec.iloc[:2]
    else:
        year_slice = contract_uec.loc[current_aniv:].iloc[:2]

    if len(year_slice) < 2:
        return 0.0

    baseline = year_slice["uec"].iloc[0]
    comparison = year_slice["uec"].iloc[1]
    if baseline is None or comparison is None:
        return 0.0
    if pd.isna(baseline) or pd.isna(comparison):
        return 0.0
    if baseline == 0:
        return 0.0

    return float(np.abs(comparison / baseline - 1))


def current_soh_from_contract_uec(
    *,
    contract_uec: pd.DataFrame,
    start: pd.Timestamp,
):
    """Get the current SOH from the contract UEC.
    Args:
        contract_uec: DataFrame with the contract UEC.
        start: Start date.

    Returns:
        Current SOH.
    """
    if contract_uec.empty:
        return 0.0

    current_uec = contract_uec.asof(start)["uec"]
    baseline = contract_uec.iloc[0]["uec"]
    if baseline in (0, None):
        return 0.0
    if pd.isna(baseline) or pd.isna(current_uec):
        return 0.0

    return float(current_uec / baseline)


# ---------------------------------------------------------------------------
# AWS
# ---------------------------------------------------------------------------


async def upload_to_aws(
    *,
    local_filename: str,
):
    """Upload the report to AWS.
    Args:
        local_filename: Local filename.

    Returns:
        None.
    """
    filename = os.path.basename(local_filename)
    bucket_name = "proximal-am-documents"
    prefix = "reports/persistent/bess_monthly_reports"
    file_key = f"{prefix}/{filename}"

    def _upload() -> None:
        s3_client = boto3.client("s3", region_name="us-east-2")
        s3_client.upload_file(local_filename, bucket_name, file_key)

    temp_dir = os.path.dirname(local_filename)
    try:
        await asyncio.to_thread(_upload)
    finally:
        if os.path.exists(local_filename):
            try:
                await asyncio.to_thread(os.remove, local_filename)
            except OSError:
                pass
        if (
            temp_dir
            and os.path.isdir(temp_dir)
            and temp_dir.startswith(tempfile.gettempdir())
        ):
            await asyncio.to_thread(shutil.rmtree, temp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------


async def generate_eec_bess_monthly_report(
    *,
    project: models.Project,
    db: AsyncSession,
    project_db: AsyncSession,
    project_db_sync: Session,
    request: BESSMonthlyReportRequest,
    tps_token: str,
):
    """Generate an EEC BESS monthly report.

    Args:
        project: The project for which to generate the report.
        db: Async database session.
        project_db: Async project database session.
        project_db_sync: Synchronous project database session.
        request: Request data including month, strategies, and commentary.
        tps_token: TPS API authentication token.
    """
    req_start = request.month
    req_end = (request.month + datetime.timedelta(days=31)).replace(day=1)
    tps_element_identifier = await get_tps_element_identifier(
        project=project,
        db=db,
    )
    temp_dir = tempfile.mkdtemp(prefix="bess_monthly_report_")
    filename = os.path.join(
        temp_dir,
        f"{project.name_short}_monthly_report_{request.month.strftime('%Y-%m')}.pdf",
    )

    contract_uec = await get_contract_uec(project=project)

    deg_rate = degradation_rate_from_contract_uec(
        contract_uec=contract_uec,
        start=pd.Timestamp(req_start),
    )

    current_soh = current_soh_from_contract_uec(
        contract_uec=contract_uec,
        start=pd.Timestamp(req_start),
    )

    request.strategies = compare_to_perfect_foresight(strategies=request.strategies)

    tps_data, tps_name, generation_hourly, consumption_hourly = await get_tps_data(
        project=project,
        parent_element_identifier=tps_element_identifier,
        start=pd.Timestamp(req_start),
        end=pd.Timestamp(req_end),
        token=tps_token,
    )
    (
        rev_breakdown_by_type_bytes,
        rev_breakdown_df,
        other_tps_data,
    ) = await generate_tps_metrics(
        tps_data=tps_data,
        tps_name=tps_name,
    )
    monthly_tbx = await get_tbx(
        project=project,
        start=pd.Timestamp(req_start),
        end=pd.Timestamp(req_end),
        token=tps_token,
        total_profit=rev_breakdown_df["Net Profit"].sum(),
    )
    # Pass real PNG bytes for rev_breakdown_by_type / bess_pcs_availability
    # when available.
    kpi_sums, kpi_means, soc_stats, degradation_rate = await get_kpi_data(
        project=project,
        project_db_sync=project_db_sync,
        start=req_start,
        end=req_end,
    )
    (
        bess_pcs_availability_bytes,
        event_summary_metrics,
        lost_capacity_mwh,
        top_ten_losses,
    ) = await build_event_data(
        project_db=project_db,
        project=project,
        start=req_start,
        end=req_end,
    )
    if top_ten_losses is not None:
        event_table = await build_event_table(
            project_db=project_db,
            top_ten_losses=top_ten_losses,
        )
    else:
        event_table = None
    possible_capacity = None
    if project.poi:
        possible_capacity = project.poi * (req_end - req_start).total_seconds() / 3600

    if possible_capacity and possible_capacity != 0:
        total_availability = 1 - (lost_capacity_mwh / possible_capacity)
        capacity_factor = (
            tps_data[tps_name]["RT_Generation_Qty"].sum() / possible_capacity
        )
    else:
        total_availability = None
        capacity_factor = None
    executive_summary_df = await generate_executive_summary(
        other_tps_data=other_tps_data,
        rev_breakdown_df=rev_breakdown_df,
        total_availability=total_availability,
        capacity_factor=capacity_factor,
        degradation_rate=degradation_rate,
        deg_rate_expected=deg_rate,
        request=request,
    )
    kpi_expected_values = {
        "monthly_cycles": (req_end - req_start).days,
        "ytd_cycles": (req_end - req_start.replace(month=1, day=1)).days,
        "lifetime_cycles": (req_end - req_start).days,
        "bess_soh": 1.00,
        "average_soc": 0.60,
        "average_resting_soc": 0.60,
        "min_soc": 0.05,
        "max_soc": 0.975,
    }

    await build_report(
        filename=filename,
        project=project,
        request=request,
        kpi_sums=kpi_sums.to_dict()["project_data"],
        kpi_means=kpi_means.to_dict()["project_data"],
        soc_stats=soc_stats,
        bess_pcs_availability_bytes=bess_pcs_availability_bytes,
        event_summary_metrics=event_summary_metrics,
        rev_breakdown_by_type_bytes=rev_breakdown_by_type_bytes,
        rev_breakdown_df=rev_breakdown_df,
        kpi_expected_values=kpi_expected_values,
        executive_summary_df=executive_summary_df,
        generation_hourly=generation_hourly,
        consumption_hourly=consumption_hourly,
        event_table=event_table,
        monthly_tbx=monthly_tbx,
        current_soh=current_soh,
    )
    await upload_to_aws(local_filename=filename)


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


type TimestampLike = datetime.datetime | datetime.date | pd.Timestamp


def _ensure_utc(ts: pd.Timestamp) -> pd.Timestamp:
    """Return the timestamp converted to or localized in UTC."""
    if ts.tz is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def covered_seconds_by_any_event(
    events: pd.DataFrame,
    start: TimestampLike,
    end: TimestampLike,
    *,
    time_start_col: str = "time_start",
    time_end_col: str = "time_end",
    ongoing_end: TimestampLike | None = None,
) -> float:
    """
    Returns the number of seconds in [start, end) that are covered by >=1 event.

    - events[time_end_col] may be null (ongoing)
    - null end is treated as `ongoing_end` if provided, otherwise `end`
    - intervals are treated as half-open: [event_start, event_end)
    """
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if end_ts <= start_ts:
        return 0.0

    ongoing_end_ts = pd.Timestamp(ongoing_end) if ongoing_end is not None else None

    if time_start_col not in events.columns or time_end_col not in events.columns:
        raise KeyError(
            f"Expected columns {time_start_col!r} and {time_end_col!r} in events."
        )

    time_start_series: pd.Series = pd.to_datetime(
        events[time_start_col],
        errors="coerce",
    )
    time_end_series: pd.Series = pd.to_datetime(
        events[time_end_col],
        errors="coerce",
    )

    time_start_dtype = time_start_series.dtype
    df_tz: datetime.tzinfo | None
    if isinstance(time_start_dtype, pd.DatetimeTZDtype):
        df_tz = time_start_dtype.tz
    else:
        df_tz = None

    if df_tz is not None:
        time_start_series = time_start_series.dt.tz_convert("UTC")
        if not time_end_series.isna().all():
            time_end_series = time_end_series.dt.tz_convert("UTC")
        start_ts = _ensure_utc(start_ts)
        end_ts = _ensure_utc(end_ts)
        if ongoing_end_ts is not None:
            ongoing_end_ts = _ensure_utc(ongoing_end_ts)
    elif start_ts.tz is not None or end_ts.tz is not None:
        time_start_series = time_start_series.dt.tz_localize("UTC")
        time_end_series = time_end_series.dt.tz_localize("UTC")
        start_ts = _ensure_utc(start_ts)
        end_ts = _ensure_utc(end_ts)
        if ongoing_end_ts is not None:
            ongoing_end_ts = _ensure_utc(ongoing_end_ts)

    df = pd.DataFrame(
        {time_start_col: time_start_series, time_end_col: time_end_series}
    )
    df = df.dropna(subset=[time_start_col])
    if df.empty:
        return 0.0

    effective_ongoing_end = ongoing_end_ts if ongoing_end_ts is not None else end_ts
    df[time_end_col] = df[time_end_col].fillna(effective_ongoing_end)

    s_clipped = df[time_start_col].where(df[time_start_col] >= start_ts, start_ts)
    s_clipped = s_clipped.where(s_clipped <= end_ts, end_ts)
    e_clipped = df[time_end_col].where(df[time_end_col] >= start_ts, start_ts)
    e_clipped = e_clipped.where(e_clipped <= end_ts, end_ts)

    clipped = pd.DataFrame({"s": s_clipped, "e": e_clipped})
    clipped = clipped[clipped["e"] > clipped["s"]]
    if clipped.empty:
        return 0.0

    clipped = clipped.sort_values(["s", "e"]).reset_index(drop=True)
    intervals: list[tuple[pd.Timestamp, pd.Timestamp]] = [
        (cast(pd.Timestamp, row.s), cast(pd.Timestamp, row.e))
        for row in clipped.itertuples(index=False)
    ]

    total_seconds = 0.0
    cur_s, cur_e = intervals[0]
    for s_i, e_i in intervals[1:]:
        if s_i <= cur_e:
            if e_i > cur_e:
                cur_e = e_i
        else:
            total_seconds += (cur_e - cur_s).total_seconds()
            cur_s, cur_e = s_i, e_i

    total_seconds += (cur_e - cur_s).total_seconds()
    return total_seconds


def covered_fraction_by_any_event(
    events: pd.DataFrame,
    start: TimestampLike,
    end: TimestampLike,
    *,
    time_start_col: str = "time_start",
    time_end_col: str = "time_end",
    ongoing_end: TimestampLike | None = None,
) -> float:
    """Fraction of [start,end) covered by >=1 event."""
    # Convert to Timestamp, handling both date and datetime inputs
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    window_seconds = (end_ts - start_ts).total_seconds()
    if window_seconds <= 0:
        return 0.0
    covered_seconds = covered_seconds_by_any_event(
        events,
        start_ts,
        end_ts,
        time_start_col=time_start_col,
        time_end_col=time_end_col,
        ongoing_end=ongoing_end,
    )
    return float(covered_seconds / window_seconds)
