import asyncio
import datetime
import os
import re
import shutil
import tempfile
import uuid
from collections.abc import Callable
from html import escape
from pathlib import Path
from typing import Any, Literal, cast

import aiohttp
import boto3
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from app.integrations.providers import ptp_explorer
from app.logger import get_logger
from core.crud.operational.contract_kpis import (
    get_contract_kpis as crud_get_contract_kpis,
)
from core.crud.operational.failure_modes import (
    get_failure_modes as crud_get_failure_modes,
)
from core.crud.operational.kpi_data import core_get_kpi_data as crud_get_kpi_data
from core.crud.operational.projects import get_projects as crud_get_projects
from core.crud.operational.qse_integrations import (
    get_qse_integration_by_project_id as crud_get_qse_integration_by_project_id,
)
from core.crud.project import events as crud_project_events
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.crud.project.devices import (
    get_project_devices_async as crud_get_project_devices_async,
)
from core.crud.project.tags import get_project_tags_v2 as crud_get_project_tags_v2
from core.db_query import OutputType
from core.domain.kpis.rte import get_project_rte as core_get_project_rte
from core.domain.kpis.rte import (
    get_project_rte_from_modules as core_get_project_rte_from_modules,
)
from core.enumerations import DeviceTypeEnum, KPITypeEnum, SensorTypeEnum, TimeInterval
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

logger = get_logger(name=__name__)


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
    included_projects: list[str] = []


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
# Additional Grouping Metadata
# ---------------------------------------------------------------------------
TRANCHE_1 = [
    "Continental",
    "Monte Cristo",
    "Gregory",
    "Palacios",
]
TRANCHE_2 = [
    "Muenster",
    "Mason",
    "Laureles",
    "Medina Lake",
    "Utopia",
    "Leaky",
    "Medina",
]
TRANCHE_3 = [
    "Sinton Pirate",
    "Falfurrias",
    "Hearn Road",
    "Gears Harris",
    "Hidden Valley",
    "Milton",
]
TRANCHE_4 = [
    "Goodwin",
    "Carrizo Springs",
    "Lyssy",
    "Escondido",
]

_TRANCHE_ORDER_GROUPS = (TRANCHE_1, TRANCHE_2, TRANCHE_3, TRANCHE_4)
PROJECT_NAME_TRANCHE_ORDER: dict[str, int] = {}
for _ti, _names in enumerate(_TRANCHE_ORDER_GROUPS):
    for _n in _names:
        PROJECT_NAME_TRANCHE_ORDER[_n] = _ti
_TRANCHE_SORT_FALLBACK = len(_TRANCHE_ORDER_GROUPS)

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
def draw_header_footer(c: canvas.Canvas, doc):  # noqa: ARG001 # no-star-syntax
    """Logos flush to the top; simple footer w/ generation date & mark.

    Args:
        c: Canvas instance used for drawing header and footer elements.
        doc: Document template; unused but required by the signature.
    """
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
    series_monthly = rev_breakdown_df.sum()

    # Create table with months as rows and services as columns
    # Prepare data: months as rows, service types as columns
    service_columns = [
        "Real-Time Energy",
        "Day-Ahead Energy",
        "Virtual Trades",
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

    for key, value in series_monthly[service_labels].items():
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
    ytd_cycles,
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
        ytd_cycles: YTD cycle count.
    Returns:
        List of flowable elements.
    """
    # two equal columns with a fixed gutter in between
    left_w = (doc.width - GUTTER_PT) / 2.0
    right_w = left_w

    # calc_delta is now imported from report_utils as calc_delta_percentage

    # ---- data ----
    soh_mean = kpi_means.get(KPITypeEnum.BESS_STRING_SOH)
    soh_actual_display = (
        format_percentage_value(value=soh_mean) if soh_mean is not None else "—"
    )
    soh_delta_display = (
        calc_delta_percentage(actual=soh_mean, expected=current_soh)
        if soh_mean is not None
        else "—"
    )
    cycle_count_sum = kpi_sums.get(KPITypeEnum.BESS_STRING_CYCLE_COUNT)
    monthly_cycles_actual = (
        f"{cycle_count_sum:.2f}" if cycle_count_sum is not None else "—"
    )
    monthly_cycles_delta = (
        calc_delta_percentage(
            actual=cycle_count_sum,
            expected=kpi_expected_values["monthly_cycles"],
        )
        if cycle_count_sum is not None
        else "—"
    )
    ytd_cycles_delta = (
        calc_delta_percentage(
            actual=ytd_cycles,
            expected=kpi_expected_values["ytd_cycles"],
        )
        if ytd_cycles is not None
        else "—"
    )
    average_soc_mean = kpi_means.get(KPITypeEnum.PROJECT_AVERAGE_SOC_PERCENT)
    average_soc_actual = (
        format_percentage_value(value=average_soc_mean)
        if average_soc_mean is not None
        else "—"
    )
    average_soc_delta = (
        calc_delta_percentage(
            actual=average_soc_mean,
            expected=kpi_expected_values["average_soc"],
        )
        if average_soc_mean is not None
        else "—"
    )
    resting_soc_mean = kpi_means.get(KPITypeEnum.BESS_STRING_RESTING_SOC_PERCENT)
    resting_soc_actual = (
        format_percentage_value(value=resting_soc_mean)
        if resting_soc_mean is not None
        else "—"
    )
    resting_soc_delta = (
        calc_delta_percentage(
            actual=resting_soc_mean,
            expected=kpi_expected_values["average_resting_soc"],
        )
        if resting_soc_mean is not None
        else "—"
    )

    kpi_rows = [
        # Metric name | Actual | Expected | Δ vs Expected
        (
            "Monthly Cycles",
            monthly_cycles_actual,
            f"{kpi_expected_values['monthly_cycles']:.2f}",
            monthly_cycles_delta,
        ),  # source: BESS Bank Cycle Count KPI
        (
            "YTD Cycles",
            f"{ytd_cycles:.2f}",
            f"{kpi_expected_values['ytd_cycles']:.2f}",
            ytd_cycles_delta,
        ),  # source: BESS Bank Cycle Count KPI
        (
            "Lifetime Cycles",
            "—",
            "—",
            "—",
        ),  # source: BESS Bank Cycle Count KPI
        (
            "BESS State of Health (%)",
            soh_actual_display,
            format_percentage_value(value=current_soh),
            soh_delta_display,
        ),  # source: BESS Bank SoH KPI
        (
            "Average SOC (%)",
            average_soc_actual,
            format_percentage_value(value=kpi_expected_values["average_soc"]),
            average_soc_delta,
        ),  # source: Project Average SOC KPI
        (
            "Average Resting SOC (%)",
            resting_soc_actual,
            format_percentage_value(value=kpi_expected_values["average_resting_soc"]),
            resting_soc_delta,
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

    def _cell_float(row: str, column: str) -> float:  # no-star-syntax
        coerced = pd.to_numeric(
            executive_summary_df.loc[row, column],
            errors="coerce",
        )
        return float(coerced)

    def _delta_str(row: str) -> str:  # no-star-syntax
        return str(executive_summary_df.loc[row, "Delta"])

    def _format_percent_cell(*, row: str, column: str) -> str:
        value = _cell_float(row=row, column=column)
        if np.isnan(value):
            return "—"
        return format_percentage_value(value=value)

    # --- Table Data (now 4 columns) ---
    executive_data: list[list[str]] = [
        ["Metric", "This Month", "Expected", "Δ vs Expected"],
        [
            "Total Revenue",
            format_dollar_value(
                value=_cell_float(row="Total Revenue", column="This Month")
            ),
            format_dollar_value(
                value=_cell_float(row="Total Revenue", column="Expected")
            ),
            _delta_str(row="Total Revenue"),
        ],
        [
            "Total Energy Discharged",
            format_energy_value(
                value=_cell_float(
                    row="Total Energy Discharged",
                    column="This Month",
                )
            ),
            format_energy_value(
                value=_cell_float(
                    row="Total Energy Discharged",
                    column="Expected",
                )
            ),
            _delta_str(row="Total Energy Discharged"),
        ],
        [
            "Total Energy Charged",
            format_energy_value(
                value=_cell_float(
                    row="Total Energy Charged",
                    column="This Month",
                )
            ),
            format_energy_value(
                value=_cell_float(
                    row="Total Energy Charged",
                    column="Expected",
                )
            ),
            _delta_str(row="Total Energy Charged"),
        ],
        [
            "Capacity-Weighted Availability",
            _format_percent_cell(
                row="Capacity-Weighted Availability", column="This Month"
            ),
            _format_percent_cell(
                row="Capacity-Weighted Availability", column="Expected"
            ),
            _delta_str(row="Capacity-Weighted Availability"),
        ],
        [
            "Market Availability",
            _format_percent_cell(row="Market Availability", column="This Month"),
            _format_percent_cell(row="Market Availability", column="Expected"),
            _delta_str(row="Market Availability"),
        ],
        [
            "Degradation Rate",
            format_percentage_per_year(
                _cell_float(row="Degradation Rate", column="This Month")
            ),
            format_percentage_per_year(
                _cell_float(row="Degradation Rate", column="Expected")
            ),
            _delta_str(row="Degradation Rate"),
        ],
        [
            "Forecast Accuracy",
            format_percentage_value(
                value=_cell_float(
                    row="Forecast Accuracy",
                    column="This Month",
                )
            ),
            format_percentage_value(
                value=_cell_float(
                    row="Forecast Accuracy",
                    column="Expected",
                )
            ),
            _delta_str(row="Forecast Accuracy"),
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
        elif row[0] == "Degradation Rate":
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
    italic_cell_style = ParagraphStyle(
        "tbx_cell_italic",
        parent=cell_style,
        fontName="Helvetica-Oblique",
    )
    italic_right_style = ParagraphStyle(
        "tbx_right_italic",
        parent=right_style,
        fontName="Helvetica-Oblique",
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
    tb_project_raw = monthly_tbx.get("project_tbx_value")
    tb_project_label = monthly_tbx.get("project_tbx_label")
    tb4_raw = monthly_tbx.get("4")

    realized_val = format_or_dash(
        value=realized_intraday_value, formatter=format_dollar_per_kw_value
    )
    tb1_val = format_or_dash(value=tb1_raw, formatter=format_dollar_per_kw_value)
    tb2_val = format_or_dash(value=tb2_raw, formatter=format_dollar_per_kw_value)
    tb_project_val = format_or_dash(
        value=tb_project_raw,
        formatter=format_dollar_per_kw_value,
    )
    tb4_val = format_or_dash(value=tb4_raw, formatter=format_dollar_per_kw_value)

    def safe_pct_capture(*, expected: float | None, actual: float | None) -> str:
        if expected is None or actual is None or expected == 0:
            return "—"
        return format_percentage_value(value=max(actual / expected, 0))

    tb1_delta = safe_pct_capture(expected=tb1_raw, actual=realized_intraday_value)
    tb2_delta = safe_pct_capture(expected=tb2_raw, actual=realized_intraday_value)
    tb_project_delta = safe_pct_capture(
        expected=tb_project_raw,
        actual=realized_intraday_value,
    )
    tb4_delta = safe_pct_capture(expected=tb4_raw, actual=realized_intraday_value)

    table_rows = [
        [
            Paragraph("Metric", header_style),
            Paragraph("Value", header_style),
            Paragraph("TB Capture", header_style),
        ],
        [
            Paragraph("Realized Value", cell_style),
            Paragraph(realized_val, right_style),
            Paragraph("—", right_style),
        ],
        [
            Paragraph(
                tb_project_label or "TB-Project",  # fallback safety
                cell_style,
            ),
            Paragraph(tb_project_val, right_style),
            Paragraph(tb_project_delta, right_style),
        ],
        [
            Paragraph("TB-1", italic_cell_style),
            Paragraph(tb1_val, italic_right_style),
            Paragraph(tb1_delta, italic_right_style),
        ],
        [
            Paragraph("TB-2", italic_cell_style),
            Paragraph(tb2_val, italic_right_style),
            Paragraph(tb2_delta, italic_right_style),
        ],
        [
            Paragraph("TB-4", italic_cell_style),
            Paragraph(tb4_val, italic_right_style),
            Paragraph(tb4_delta, italic_right_style),
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


def build_portfolio_kpi_table_rows(
    *,
    df: pd.DataFrame | None,
    styles,
    selected_project: str | None,
) -> list[list[Paragraph]]:
    """Build table rows for portfolio KPI comparison.

    Args:
        df: DataFrame with projects as index and KPI columns as values.
        styles: ReportLab stylesheet mapping.
        selected_project: Name of the current project to highlight in bold.
    """

    if df is None or df.empty:
        return []

    header_style = ParagraphStyle(
        "radar_header",
        parent=styles["body"],
        fontName="Helvetica-Bold",
        alignment=1,
    )
    left_style = ParagraphStyle(
        "radar_left",
        parent=styles["body"],
        alignment=0,
    )
    right_style = ParagraphStyle(
        "radar_right",
        parent=styles["body"],
        alignment=2,
    )

    column_order = list(df.columns)

    def portfolio_project_sort_key(idx):  # no-star-syntax
        """Return a sort key list for ordering portfolio project index labels.

        Args:
            idx: Sequence of index labels to produce sort keys for.
        """

        def row_key(x: str) -> tuple[int, int, str]:  # no-star-syntax
            if x == selected_project:
                return (0, 0, "")
            if x == "Portfolio Mean":
                return (2, 0, "")
            tranche_i = PROJECT_NAME_TRANCHE_ORDER.get(x, _TRANCHE_SORT_FALLBACK)
            return (1, tranche_i, x.casefold())

        return [row_key(str(x)) for x in idx]

    df = df.sort_index(key=portfolio_project_sort_key)

    header_row = [
        Paragraph("<b>Project</b>", header_style),
        *[Paragraph(f"<b>{column}</b>", header_style) for column in column_order],
    ]
    table_rows: list[list[Paragraph]] = [header_row]

    for project_name, row in df.iterrows():
        display_name = (
            f"<b>{project_name}</b>"
            if selected_project is not None and project_name == selected_project
            else project_name
        )
        row_cells = [Paragraph(display_name, left_style)]
        for column in column_order:
            value = row.get(column)
            if pd.isna(value):
                formatted_value = "—"
            elif (
                column == "Availability (%)"
                or column == "RTE (%)"
                or column == "Balance of Strings"
            ):
                formatted_value = format_percentage_value(value=value)
            elif column == "Energy Yield (MWh/MW)":
                formatted_value = f"{value:.2f}"
            elif column == "Real $ / MWh Delivered":
                v = float(value)
                formatted_value = f"-${abs(v):,.0f}" if v < 0 else f"${v:,.0f}"
            elif column == "Virtual $ / MWh Volume":
                v = float(value)
                formatted_value = f"-${abs(v):,.2f}" if v < 0 else f"${v:,.2f}"
            else:
                formatted_value = f"{value:.2f}"
            row_cells.append(Paragraph(formatted_value, right_style))
        table_rows.append(row_cells)

    return table_rows


def section_portfolio_kpi_comparison(
    *,
    doc,
    styles,
    radar_chart_bytes: bytes,
    radar_table_rows: list[list[Paragraph]] | None,
):
    """Create the portfolio KPI comparison section.

    Args:
        doc: Document template used to determine layout dimensions.
        styles: Mapping of style names to ReportLab paragraph styles.
        radar_chart_bytes: PNG/SVG bytes of the rendered radar chart image.
        radar_table_rows: Rows of Paragraph cells for the KPI table, or
            None if no table should be rendered.
    """

    title = Paragraph("<b>Portfolio KPI Comparison</b>", styles["h2_center"])
    radar_image = load_image_from_source(radar_chart_bytes)
    radar_image = img_fit_by_width(
        img=radar_image,
        target_w=doc.width * 0.6,
    )
    radar_image.hAlign = "CENTER"

    flowables: list = [
        title,
        Spacer(1, 0.12 * inch),
        radar_image,
    ]

    if radar_table_rows:
        table = Table(
            radar_table_rows,
            colWidths=[
                doc.width * 0.22,
                doc.width * 0.116,
                doc.width * 0.116,
                doc.width * 0.116,
                doc.width * 0.116,
                doc.width * 0.116,
            ],
            hAlign="LEFT",
        )
        table_style = tstyle_gridded_table(
            header_bg=colors.lightgrey,
            row_bg_alt=colors.HexColor("#F7F7F7"),
        )
        table.setStyle(table_style)
        table.hAlign = "CENTER"
        flowables.extend(
            [
                Spacer(1, 0.16 * inch),
                table,
            ]
        )

    flowables.append(Spacer(1, 0.24 * inch))
    return flowables


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
            """Wrap text in a styled Paragraph for a table body cell.

            Args:
                text: Cell text content to display.
                align: Horizontal alignment; one of 'left', 'center', or 'right'.
            """
            safe_text = escape(str(text))
            style = {"left": cell_left, "center": cell_center, "right": cell_right}[
                align
            ]
            return Paragraph(safe_text, style)

        def header_cell(*, text: str):
            """Wrap text in a styled Paragraph for a table header cell.

            Args:
                text: Header label text to display.
            """
            return Paragraph(escape(str(text)), header_style)

        # --- build data ---
        if event_table is not None and not event_table.empty:
            df = event_table.copy()

            sort_cols = [c for c in df.columns if c.lower().startswith("capacity loss")]
            if sort_cols:
                df = df.sort_values(by=sort_cols, ascending=False)

            def fmt_dt(*, val):
                """Format a datetime value as a human-readable string.

                Args:
                    val: Datetime-like value to format, or NaN/None.
                """
                if pd.isna(val):
                    return "—"
                try:
                    return pd.Timestamp(val).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    return str(val)

            def fmt_val(*, val, is_currency: bool = False):
                """Format a numeric value as a plain or currency string.

                Args:
                    val: Numeric value to format, or NaN/None.
                    is_currency: When True, prefix the value with a dollar sign.
                """
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
    """Render a notice when no event data is available for the reporting period.

    Args:
        doc: Document template used to determine layout dimensions.
        styles: Mapping of style names to ReportLab paragraph styles.
        message: Notice text to display inside the highlighted box.
    """
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
) -> list[Any]:
    """Create net energy flow overview section.

    Args:
        doc: Document template.
        styles: Style dictionary.
        generation_hourly: DataFrame with generation hourly data.
        consumption_hourly: DataFrame with consumption hourly data.
    """
    title = Paragraph(
        "<para align='center'>Net Energy Flow</para>",
        styles["h2_center"],
    )
    section_elements = [
        title,
        Spacer(1, 0.12 * inch),
    ]

    heading = Paragraph("<b>Net Energy Flow (MWh)</b>", styles["body_center"])

    if (
        generation_hourly is None
        or generation_hourly.empty
        or consumption_hourly is None
        or consumption_hourly.empty
    ):
        section_elements.extend(
            [
                heading,
                Spacer(1, 0.05 * inch),
                Paragraph("No data available.", styles["body_center"]),
                Spacer(1, 0.15 * inch),
                PageBreak(),
            ]
        )
        return section_elements

    gen_df = generation_hourly.sort_index()
    cons_df = consumption_hourly.sort_index()

    # Align indexes/columns and compute net = generation - consumption,
    # with consumption represented as negative values.
    gen_aligned, cons_aligned = gen_df.align(cons_df, join="outer")
    cons_negative = -cons_aligned
    net_df = gen_aligned.add(cons_negative, fill_value=0.0)

    net_df = net_df.reindex(sorted(net_df.columns), axis=1)

    columns = list(net_df.columns)
    numeric_block = net_df[columns].to_numpy(dtype=float, copy=True)
    numeric_vals = numeric_block[~np.isnan(numeric_block)]

    if numeric_vals.size:
        min_val = float(np.nanmin(numeric_vals))
        max_val = float(np.nanmax(numeric_vals))
    else:
        min_val = None
        max_val = None

    def format_col(*, col_val: Any) -> str:
        try:
            col_int = int(col_val)
        except (TypeError, ValueError):
            return str(col_val)
        return f"{col_int:02d}:00"

    def format_idx(*, idx_val: Any) -> str:
        if isinstance(idx_val, (datetime.datetime, datetime.date)):
            return pd.Timestamp(idx_val).strftime("%b %d")
        return str(idx_val)

    def format_val(*, raw_val: Any) -> str:
        if pd.isna(raw_val):
            return "—"
        return f"{raw_val:.2f}"

    table_data = [
        ["Date"] + [format_col(col_val=col) for col in columns],
    ]
    for idx_val, row in net_df.iterrows():
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
        # Diverging color scale: negatives -> red, positives -> green, zero -> white.
        neg_extent = abs(min_val) if min_val < 0 else 0.0
        pos_extent = max_val if max_val > 0 else 0.0

        def interpolate_color(
            *, base_rgb: tuple[float, float, float], frac: float
        ) -> colors.Color:
            frac_clamped = max(0.0, min(frac, 1.0))
            r = 1 - frac_clamped * (1 - base_rgb[0])
            g = 1 - frac_clamped * (1 - base_rgb[1])
            b = 1 - frac_clamped * (1 - base_rgb[2])
            return colors.Color(r, g, b)

        green_rgb = (0.72, 0.9, 0.72)
        red_rgb = (0.96, 0.75, 0.75)

        style_updates: list[tuple] = []
        for row_idx, idx_val in enumerate(net_df.index, start=1):
            for col_idx, col in enumerate(columns, start=1):
                raw_value = net_df.at[idx_val, col]
                numeric_value = float(pd.to_numeric(raw_value, errors="coerce"))
                if pd.isna(numeric_value) or numeric_value == 0:
                    continue
                if numeric_value > 0 and pos_extent > 0:
                    frac = numeric_value / pos_extent
                    color = interpolate_color(base_rgb=green_rgb, frac=frac)
                elif numeric_value < 0 and neg_extent > 0:
                    frac = abs(numeric_value) / neg_extent
                    color = interpolate_color(base_rgb=red_rgb, frac=frac)
                else:
                    continue
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

    section_elements.extend(
        [
            heading,
            Spacer(1, 0.05 * inch),
            tbl,
            Spacer(1, 0.18 * inch),
        ]
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
    radar_table_df: pd.DataFrame | None = None,
    radar_selected_project: str | None = None,
    radar_chart_bytes: bytes | None = None,
    ytd_cycles: float | None = None,
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
        radar_table_df: Optional dataframe containing raw KPI comparison values.
        radar_selected_project: Optional project name to highlight in comparison table.
        radar_chart_bytes: Optional radar chart image bytes.
        ytd_cycles: Optional YTD cycle count.
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
        ytd_cycles=ytd_cycles,
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

    if radar_chart_bytes is not None:
        radar_table_rows = (
            build_portfolio_kpi_table_rows(
                df=radar_table_df,
                styles=styles,
                selected_project=radar_selected_project,
            )
            if radar_table_df is not None
            else None
        )
        elements.append(PageBreak())
        elements += section_portfolio_kpi_comparison(
            doc=doc,
            styles=styles,
            radar_chart_bytes=radar_chart_bytes,
            radar_table_rows=radar_table_rows,
        )

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
    start_dt: datetime.date,
    end_dt: datetime.date,
    token: str,
):
    """
    Get TPS data from the PTP API.

    Args:
        project: Project model instance.
        parent_element_identifier: Parent element identifier.
        start_dt: Start date.
        end_dt: End date.
        token: API authentication token.

    Returns:
        Tuple of (revenue breakdown DataFrame, generation hourly DataFrame,
        consumption hourly DataFrame, virtual volume).
    """

    def df_generator_settlement_frame(
        *,
        element: dict[str, Any],
        interval_start_utc: Any,
        project_time_zone: str,
    ) -> pd.DataFrame:
        df = pd.DataFrame(
            index=interval_start_utc,
            data=element["DataPoints"],
        )
        df.index = pd.to_datetime(df.index)
        df.index = df.index.tz_convert(project_time_zone)
        return df

    def build_daily_dataframe(*, df_all_in: pd.DataFrame) -> pd.DataFrame:
        df_all = df_all_in.drop(
            columns=list(DROP_COLUMNS & set(df_all_in.columns)),
            errors="ignore",
        )

        df_daily = df_all.groupby(pd.Grouper(freq="D")).sum()

        ancillary_series = -(
            (df_daily[ANCILLARY_FIELDS_DA] / 4).sum(axis=1)
            + df_daily[ANCILLARY_FIELDS_RT].sum(axis=1)
        )

        df_actuals = pd.DataFrame(index=df_daily.index)
        df_actuals["Day-Ahead Energy"] = (
            -df_daily[["DAESAMT", "DAEPAMT"]].sum(axis=1) / 4
        )
        df_actuals["Real-Time Energy"] = -df_daily[["RTEIAMT"]].sum(axis=1)
        df_actuals["Misc Charges"] = -df_daily[["BPDAMT", "SPDAMT"]].sum(axis=1)
        df_actuals["Virtual Trades"] = virtual_series
        df_actuals["Ancillary Services"] = ancillary_series
        df_actuals["Net Profit"] = df_actuals.sum(axis=1)

        return df_actuals

    REQUIRED_COLUMNS = {
        "DAESAMT",
        "DAEPAMT",
        "RTEIAMT",
        "BPDAMT",
        "SPDAMT",
        "RTRDASIAMT",
        "PCRUAMT",
        "PCRDAMT",
        "PCRRAMT",
        "PCNSAMT",
        "PCECRAMT",
        "RTRUIMBAMT",
        "RTRRIMBAMT",
        "RTNSIMBAMT",
        "RTECRIMBAMT",
        "TWTG",
    }

    DROP_COLUMNS = {"RESOURCE_ID", "SETTLEMENT_POINT"}

    ANCILLARY_FIELDS_DA = [
        "PCRUAMT",
        "PCRDAMT",
        "PCRRAMT",
        "PCNSAMT",
        "PCECRAMT",
    ]
    ANCILLARY_FIELDS_RT = [
        "RTRUIMBAMT",
        "RTRDASIAMT",
        "RTRRIMBAMT",
        "RTNSIMBAMT",
        "RTECRIMBAMT",
    ]

    DA_fields = ["DAES", "DAESAMT", "DAEP", "DAEPAMT"]

    start = pd.Timestamp(start_dt, tz=project.time_zone)
    end = pd.Timestamp(end_dt, tz=project.time_zone)
    headers = {"Authorization": f"Bearer {token}"}

    virtual_url = (
        "https://api.ptp.energy/ptp/ERCOTNodal/Virtual-Settlement-Data/query-columnar"
    )
    virtual_params = {
        "begin": start.tz_convert("UTC").strftime("%Y-%m-%d %H:%M:%S"),
        "end": end.tz_convert("UTC").strftime("%Y-%m-%d %H:%M:%S"),
        "elementQueryMode": "byParentAndFilter",
        "elementIdentifiers": [parent_element_identifier],
    }
    generator_url = (
        "https://api.ptp.energy/ptp/ERCOTNodal/Generator-Settlement-Data/query-columnar"
    )
    generator_params = {
        "begin": start.tz_convert("UTC").strftime("%Y-%m-%d %H:%M:%S"),
        "end": end.tz_convert("UTC").strftime("%Y-%m-%d %H:%M:%S"),
        "elementQueryMode": "byParentAndFilter",
        "elementIdentifiers": [parent_element_identifier],
    }

    async def _fetch_json(
        *,
        session: aiohttp.ClientSession,
        url: str,
        request_params: dict[str, Any],
    ) -> dict[str, Any] | None:
        try:
            async with session.get(
                url, headers=headers, params=request_params
            ) as response:
                status = response.status
                payload = cast(dict[str, Any], await response.json())
        except aiohttp.ClientError as exc:
            logger.warning("Failed to fetch TPS data from %s: %s", url, exc)
            return None
        if status >= 400:
            logger.warning("TPS data request to %s failed with status %s", url, status)
            return None
        return payload

    async with aiohttp.ClientSession() as session:
        virtual_payload = await _fetch_json(
            session=session,
            url=virtual_url,
            request_params=virtual_params,
        )
        generator_payload = await _fetch_json(
            session=session,
            url=generator_url,
            request_params=generator_params,
        )

    virtual_data = cast(dict[str, Any], (virtual_payload or {}).get("data", {}))
    daily_dfs: list[pd.DataFrame] = []
    elements = cast(list[dict[str, Any]], virtual_data.get("Elements", []))
    if not elements:
        virtual_series = pd.Series()
        virtual_volume = float(0)
    else:
        for element in elements:
            daily_start = pd.Timestamp(element["GoLiveDate"], tz=project.time_zone)
            daily_end = pd.Timestamp(
                element["ExpirationDate"], tz=project.time_zone
            ) + pd.Timedelta(days=1)
            daily_df = pd.DataFrame(
                index=virtual_data["IntervalEndUtc"], data=element["DataPoints"]
            )
            daily_df.index = pd.to_datetime(daily_df.index)
            daily_df.index = daily_df.index.tz_convert(project.time_zone)
            daily_df = daily_df.loc[daily_start:daily_end]
            daily_dfs.append(daily_df)
        df_virtuals = pd.concat(daily_dfs).sort_index()
        df_virtuals = df_virtuals.drop(columns=["Settlement_Point"])
        df_virtuals = df_virtuals.groupby(level=0).sum()
        df_virtuals.index = pd.to_datetime(df_virtuals.index) - pd.Timedelta(minutes=15)
        DA_fields_present = df_virtuals.columns.intersection(DA_fields)
        df_virtuals[DA_fields_present] /= 4
        df_virtuals = df_virtuals.fillna(0)
        virtual_series = (
            -df_virtuals.loc[:, df_virtuals.columns.str.contains("AMT")]
            .groupby(pd.Grouper(freq="D"))
            .sum()
            .sum(axis=1)
        )
        virtual_volume = float(
            df_virtuals.loc[:, ~df_virtuals.columns.str.contains("AMT")]
            .abs()
            .sum()
            .sum()
        )

    if generator_payload is None:
        raise ValueError("Failed to fetch generator settlement data.")

    generator_data = generator_payload.get("data")
    if generator_data is None:
        raise ValueError("Missing generator settlement response data.")

    generator_elements = cast(list[dict[str, Any]], generator_data.get("Elements", []))
    if not generator_elements:
        raise ValueError("Generator settlement response missing elements.")

    selected_element: dict[str, Any] | None = None
    best_candidate: dict[str, Any] | None = None
    best_candidate_keys: set[str] = set()

    for candidate in generator_elements:
        data_points = candidate.get("DataPoints")
        if not data_points:
            continue

        if not isinstance(data_points, dict):
            continue

        candidate_keys = set(data_points.keys())
        if len(REQUIRED_COLUMNS & candidate_keys) > len(
            REQUIRED_COLUMNS & best_candidate_keys
        ):
            best_candidate = candidate
            best_candidate_keys = candidate_keys

        if REQUIRED_COLUMNS.issubset(candidate_keys):
            selected_element = candidate
            break

    if selected_element is None:
        if best_candidate is None:
            raise ValueError(
                "Could not find generator settlement element with required columns."
            )
        selected_element = best_candidate

    df_all = df_generator_settlement_frame(
        element=selected_element,
        interval_start_utc=generator_data["IntervalStartUtc"],
        project_time_zone=project.time_zone,
    )
    missing_df_all = REQUIRED_COLUMNS - set(df_all.columns)
    if missing_df_all:
        for col in sorted(missing_df_all):
            df_all[col] = 0.0

    rev_breakdown_df = build_daily_dataframe(df_all_in=df_all)

    meter = df_all["TWTG"]
    hourly_gen = meter[meter >= 0].resample("1h").sum()
    hourly_cons = meter[meter <= 0].resample("1h").sum()

    df_hr_gen = hourly_gen.to_frame(name="value").assign(
        date=lambda x: pd.to_datetime(x.index).date,
        hour=lambda x: pd.to_datetime(x.index).hour,
    )
    df_hr_cons = hourly_cons.to_frame(name="value").assign(
        date=lambda x: pd.to_datetime(x.index).date,
        hour=lambda x: pd.to_datetime(x.index).hour,
    )

    generation_hourly = df_hr_gen.pivot(index="date", columns="hour", values="value")
    consumption_hourly = df_hr_cons.pivot(
        index="date", columns="hour", values="value"
    ).abs()

    return (
        rev_breakdown_df,
        generation_hourly,
        consumption_hourly,
        virtual_volume,
    )


async def generate_revenue_breakdown_chart(
    *,
    rev_breakdown_df: pd.DataFrame,
):
    """Generate revenue breakdown chart and metrics from TPS data.

    Args:
        rev_breakdown_df: DataFrame with revenue breakdown data.

    Returns:
        Tuple of (chart_bytes, report_df).
    """

    # Separate columns (excluding Net Profit for bars)
    bar_columns = [col for col in rev_breakdown_df.columns if col != "Net Profit"]

    # Create chart using utility function
    fig = create_stacked_bar_chart(
        df=rev_breakdown_df,
        bar_columns=bar_columns,
        line_column="Net Profit",
        title="Revenue Breakdown by Type",
        xaxis_tickformat="%b %d, %Y",
        yaxis_format="$,.0f",
    )

    rev_breakdown_by_type_bytes = fig.to_image(format="png")
    return rev_breakdown_by_type_bytes


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
    if project.poi is None or project.poi == 0:
        project_tbx = round(
            project.capacity_bess_energy_bol_dc / project.capacity_bess_power_ac, 1
        )
    else:
        project_tbx = round(project.capacity_bess_energy_bol_dc / project.poi, 1)

    def _partial_cycle_sum(
        *, values: np.ndarray, count: float, select: Literal["bottom", "top"]
    ) -> float:
        """Return the partial sum for fractional cycle counts on sorted arrays.

        Args:
            values: Array of hourly energy values for a single day.
            count: Number of cycles (may be fractional) to select.
            select: Which end of the sorted array to sum ("bottom" or "top").
        """
        if count <= 0:
            return 0.0
        sorted_values = np.sort(values)
        whole = int(count)
        frac = count - whole
        total = 0.0

        if select == "bottom":
            if whole > 0:
                total += float(sorted_values[:whole].sum())
            if frac > 0 and whole < len(sorted_values):
                total += float(sorted_values[whole] * frac)
        else:
            if whole > 0:
                total += float(sorted_values[-whole:].sum())
            if frac > 0:
                index = len(sorted_values) - whole - 1
                if index >= 0:
                    total += float(sorted_values[index] * frac)
        return total

    daily_tbx = pd.DataFrame()
    cycle_sizes = [1.0, project_tbx, 2.0, 4.0]
    seen_cycle_sizes: set[float] = set()
    ordered_cycle_sizes: list[float] = []
    for size in cycle_sizes:
        if size not in seen_cycle_sizes:
            ordered_cycle_sizes.append(size)
            seen_cycle_sizes.add(size)

    for x in ordered_cycle_sizes:
        for date in work["date"].unique():
            arr = grouped.loc[date].to_numpy()
            bottom = _partial_cycle_sum(values=arr, count=x, select="bottom")
            top = _partial_cycle_sum(values=arr, count=x, select="top")
            tbx = (top - bottom) / 1000
            daily_tbx.loc[date, f"{x:g}"] = tbx
    daily_tbx.index = pd.to_datetime(daily_tbx.index)
    daily_tbx = daily_tbx.sort_index()
    monthly_tbx = daily_tbx.groupby(pd.Grouper(freq="ME")).sum()
    monthly_records = monthly_tbx.to_dict(orient="records")
    project_tbx_key = f"{project_tbx:g}"

    if not monthly_records:
        project_label = f"TB-{project_tbx_key}"
        return {
            "1": 0.0,
            project_tbx_key: 0.0,
            "2": 0.0,
            "4": 0.0,
            "realized_intraday_value": 0.0,
            "project_tbx_value": 0.0,
            "project_tbx_label": project_label,
        }
    tbx_dict = monthly_records[0]
    project_label = f"TB-{project_tbx_key}"
    if project.poi is None or project.poi == 0:
        tbx_dict["realized_intraday_value"] = 0
    tbx_dict["realized_intraday_value"] = total_profit / project.poi / 1000
    tbx_dict["project_tbx_value"] = tbx_dict.get(project_tbx_key, 0.0)
    tbx_dict["project_tbx_label"] = project_label
    return tbx_dict


# ---------------------------------------------------------------------------
# Proximal Data
# ---------------------------------------------------------------------------


async def get_tps_element_identifier(
    *,
    project: models.Project,
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
    qse_integration_query = crud_get_qse_integration_by_project_id(
        project_id=project.project_id,
    )
    qse_integration = await qse_integration_query.get_async(
        output_type=OutputType.SQLALCHEMY,
    )
    if qse_integration is None:
        raise KeyError("QSE integration not found")
    if qse_integration.qse_project_identifier is None:
        raise KeyError("QSE project identifier not configured")
    return cast(str, qse_integration.qse_project_identifier)


def _get_qse_resource_id(
    *,
    qse_integration: models.QSEIntegration,
) -> str | None:
    """Extract resource_id from QSE integration provider config.

    Args:
        qse_integration: QSE integration model instance.
    """
    provider_config = qse_integration.provider_config
    if not isinstance(provider_config, dict):
        return None
    resource_id = provider_config.get("resource_id")
    if not resource_id:
        return None
    return str(resource_id)


def _parse_ptp_datetime(*, raw_value: Any) -> pd.Timestamp | None:
    """Parse a PTP datetime value into a UTC timestamp.

    Args:
        raw_value: Raw value from the PTP API response.
    """
    if not isinstance(raw_value, str):
        return None
    parsed = pd.to_datetime(raw_value, utc=True, errors="coerce")
    if pd.isna(parsed):
        return None
    return cast(pd.Timestamp, parsed)


def _parse_ptp_float(*, raw_value: Any) -> float | None:
    """Parse a PTP numeric value into float.

    Args:
        raw_value: Raw value from the PTP API response.
    """
    if isinstance(raw_value, (int, float)):
        parsed = float(raw_value)
        if np.isnan(parsed):
            return None
        return parsed
    if not isinstance(raw_value, str):
        return None
    stripped = raw_value.replace(",", "").strip()
    if not stripped:
        return None
    try:
        parsed = float(stripped)
    except ValueError:
        return None
    if np.isnan(parsed):
        return None
    return parsed


def _extract_ticket_data_points(*, entry: dict[str, Any]) -> dict[str, Any]:
    """Extract first data value for each ticket data point key.

    Args:
        entry: Raw ticket entry dict from the PTP API response.
    """
    ticket_data_points: dict[str, Any] = {}
    for data_point in entry.get("dataPoints", []):
        if not isinstance(data_point, dict):
            continue
        key_name = data_point.get("keyName")
        if not isinstance(key_name, str):
            continue
        values = data_point.get("values", [])
        if not isinstance(values, list):
            continue
        for value_item in values:
            if not isinstance(value_item, dict):
                continue
            data_items = value_item.get("data", [])
            if not isinstance(data_items, list):
                continue
            for data_item in data_items:
                if not isinstance(data_item, dict):
                    continue
                value = data_item.get("value")
                if value is not None:
                    ticket_data_points[key_name] = value
                    break
            if key_name in ticket_data_points:
                break
    return ticket_data_points


def _ticket_interval(
    *,
    ticket_data_points: dict[str, Any],
) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    """Return outage interval start and end for a ticket.

    Args:
        ticket_data_points: Flat key→value map from `_extract_ticket_data_points`.
    """
    start = _parse_ptp_datetime(raw_value=ticket_data_points.get("ActualStartTime"))
    if start is None:
        start = _parse_ptp_datetime(
            raw_value=ticket_data_points.get("PlannedStartTime")
        )

    end = _parse_ptp_datetime(raw_value=ticket_data_points.get("ActualEndTime"))
    if end is None:
        end = _parse_ptp_datetime(raw_value=ticket_data_points.get("PlannedEndTime"))

    return start, end


def _ticket_available_capacity_mw(
    *,
    ticket_data_points: dict[str, Any],
) -> float | None:
    """Return ticket available MW as abs(LSL) + abs(HSL).

    Args:
        ticket_data_points: Flat key→value map from `_extract_ticket_data_points`.
    """
    lsl = _parse_ptp_float(raw_value=ticket_data_points.get("LSL"))
    hsl = _parse_ptp_float(raw_value=ticket_data_points.get("HSL"))
    if lsl is None or hsl is None:
        return None
    return abs(lsl) + abs(hsl)


async def _find_outage_element_identifier(
    *,
    token: str,
    resource_name: str,
    begin_utc: pd.Timestamp,
    end_utc: pd.Timestamp,
) -> str | None:
    """Find outage endpoint element identifier by resource name.

    Args:
        token: PTP API authentication token.
        resource_name: Resource name string to match against PTP entry names.
        begin_utc: Query window start in UTC.
        end_utc: Query window end in UTC.
    """
    begin = begin_utc.isoformat().replace("+00:00", "Z")
    end = end_utc.isoformat().replace("+00:00", "Z")
    data = await ptp_explorer.get_endpoint_data(
        token=token,
        market="Operations",
        endpoint="Outage-Ticket-Data-ERCOT",
        begin=begin,
        end=end,
    )
    entries = data.get("data")
    if not isinstance(entries, list):
        return None

    normalized_resource = resource_name.strip().upper()
    best_match_identifier: str | None = None
    best_match_score: int | None = None

    for entry in entries:
        if not isinstance(entry, dict) or entry.get("definition") != "Equipment":
            continue
        entry_name = str(entry.get("element", "")).strip().upper()
        identifier = entry.get("identifier")
        if not isinstance(identifier, str) or not entry_name:
            continue
        if entry_name == normalized_resource:
            return identifier

        entry_tokens = re.split(r"[^A-Z0-9]+", entry_name)
        if normalized_resource in entry_tokens:
            score = len(entry_name) - len(normalized_resource)
            if best_match_score is None or score < best_match_score:
                best_match_identifier = identifier
                best_match_score = score

    return best_match_identifier


async def get_market_outage_tickets(
    *,
    project: models.Project,
    token: str,
    start: datetime.date,
    end: datetime.date,
) -> pd.DataFrame:
    """Get outage tickets active during the report period.

    Args:
        project: Project model instance.
        token: PTP API authentication token.
        start: Inclusive report-period start date.
        end: Exclusive report-period end date.

    Returns:
        DataFrame with outage rows containing `time_start`, `time_end`,
        and `available_capacity_mw`.
    """
    qse_integration_query = crud_get_qse_integration_by_project_id(
        project_id=project.project_id,
    )
    qse_integration = await qse_integration_query.get_async(
        output_type=OutputType.SQLALCHEMY
    )
    if qse_integration is None:
        logger.warning(
            "QSE integration missing for project_id=%s",
            project.project_id,
        )
        return pd.DataFrame(columns=["time_start", "time_end", "available_capacity_mw"])

    resource_name = _get_qse_resource_id(qse_integration=qse_integration)
    if resource_name is None:
        logger.warning(
            "QSE provider_config missing resource_id for %s",
            project.project_id,
        )
        return pd.DataFrame(columns=["time_start", "time_end", "available_capacity_mw"])

    period_start = pd.Timestamp(start, tz=project.time_zone).tz_convert("UTC")
    period_end = pd.Timestamp(end, tz=project.time_zone).tz_convert("UTC")
    query_begin = period_start - pd.Timedelta(days=31)

    element_identifier = await _find_outage_element_identifier(
        token=token,
        resource_name=resource_name,
        begin_utc=query_begin,
        end_utc=period_end,
    )
    if element_identifier is None:
        return pd.DataFrame(columns=["time_start", "time_end", "available_capacity_mw"])

    data = await ptp_explorer.get_endpoint_data(
        token=token,
        market="Operations",
        endpoint="Outage-Ticket-Data-ERCOT",
        elements=[element_identifier],
        begin=query_begin.isoformat().replace("+00:00", "Z"),
        end=period_end.isoformat().replace("+00:00", "Z"),
    )
    entries = data.get("data")
    if not isinstance(entries, list):
        return pd.DataFrame(columns=["time_start", "time_end", "available_capacity_mw"])

    ticket_intervals: list[dict[str, pd.Timestamp | None | float]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("definition") != "Ticket Item":
            continue
        ticket_data_points = _extract_ticket_data_points(entry=entry)
        interval_start, interval_end = _ticket_interval(
            ticket_data_points=ticket_data_points
        )
        available_capacity_mw = _ticket_available_capacity_mw(
            ticket_data_points=ticket_data_points
        )
        if interval_start is None:
            continue
        if available_capacity_mw is None:
            logger.debug(
                "Skipping outage ticket without LSL/HSL for project_id=%s",
                project.project_id,
            )
            continue
        ticket_intervals.append(
            {
                "time_start": interval_start,
                "time_end": interval_end,
                "available_capacity_mw": available_capacity_mw,
            }
        )

    if not ticket_intervals:
        return pd.DataFrame(columns=["time_start", "time_end", "available_capacity_mw"])

    tickets_df = pd.DataFrame(ticket_intervals)
    effective_end = tickets_df["time_end"].fillna(period_end)
    active_mask = (tickets_df["time_start"] < period_end) & (
        effective_end > period_start
    )
    return tickets_df.loc[active_mask].copy()


def _capacity_weighted_availability(
    *,
    tickets_df: pd.DataFrame,
    period_start: pd.Timestamp,
    period_end: pd.Timestamp,
    max_capacity_mw: float,
) -> float:
    """Calculate availability from ticket capacities over time.

    Uses max available capacity when there is no active ticket. For overlapping
    tickets, uses the most restrictive (minimum) available capacity.

    Args:
        tickets_df: DataFrame with `time_start`, `time_end`, and
            `available_capacity_mw` columns.
        period_start: Availability window start (UTC).
        period_end: Availability window end (UTC).
        max_capacity_mw: Nameplate capacity used as the no-outage baseline.
    """
    if period_end <= period_start or max_capacity_mw <= 0:
        return 0.0

    clipped = tickets_df.copy()
    clipped["time_end"] = clipped["time_end"].fillna(period_end)
    clipped["time_start"] = clipped["time_start"].where(
        clipped["time_start"] >= period_start,
        period_start,
    )
    clipped["time_end"] = clipped["time_end"].where(
        clipped["time_end"] <= period_end,
        period_end,
    )
    clipped = clipped[clipped["time_end"] > clipped["time_start"]].copy()
    if clipped.empty:
        return 1.0

    events: list[tuple[pd.Timestamp, int, float]] = []
    for row in clipped.itertuples(index=False):
        start_ts = cast(pd.Timestamp, row.time_start)
        end_ts = cast(pd.Timestamp, row.time_end)
        capacity = float(cast(float | int, row.available_capacity_mw))
        bounded_capacity = float(np.clip(capacity, 0.0, max_capacity_mw))
        events.append((start_ts, 1, bounded_capacity))
        events.append((end_ts, 0, bounded_capacity))

    events.sort(key=lambda x: (x[0], x[1]))
    active_caps: list[float] = []
    weighted_capacity_seconds = 0.0
    current_ts = period_start

    for event_ts, is_start, capacity in events:
        if event_ts > current_ts:
            active_capacity = min(active_caps) if active_caps else max_capacity_mw
            weighted_capacity_seconds += (
                event_ts - current_ts
            ).total_seconds() * active_capacity
            current_ts = event_ts

        if is_start == 1:
            active_caps.append(capacity)
        elif capacity in active_caps:
            active_caps.remove(capacity)

    if current_ts < period_end:
        active_capacity = min(active_caps) if active_caps else max_capacity_mw
        weighted_capacity_seconds += (
            period_end - current_ts
        ).total_seconds() * active_capacity

    max_capacity_seconds = (period_end - period_start).total_seconds() * max_capacity_mw
    if max_capacity_seconds <= 0:
        return 0.0
    return float(np.clip(weighted_capacity_seconds / max_capacity_seconds, 0.0, 1.0))


async def get_market_availability(
    *,
    project: models.Project,
    token: str,
    start: datetime.date,
    end: datetime.date,
) -> float | None:
    """Calculate market availability for report period from outage tickets.

    Args:
        project: Project model instance.
        token: PTP API authentication token.
        start: Inclusive report-period start date.
        end: Exclusive report-period end date.

    Returns:
        Fractional availability between 0.0 and 1.0, or None on error.
    """
    period_start = pd.Timestamp(start, tz=project.time_zone).tz_convert("UTC")
    period_end = pd.Timestamp(end, tz=project.time_zone).tz_convert("UTC")
    if period_end <= period_start:
        return None
    if project.poi is None:
        return None
    max_capacity_mw = float(2 * abs(project.poi))
    if max_capacity_mw <= 0:
        return None

    try:
        tickets_df = await get_market_outage_tickets(
            project=project,
            token=token,
            start=start,
            end=end,
        )
    except Exception:
        logger.exception(
            "Failed retrieving outage tickets for project_id=%s",
            project.project_id,
        )
        return None

    if tickets_df.empty:
        return 1.0

    return _capacity_weighted_availability(
        tickets_df=tickets_df,
        period_start=period_start,
        period_end=period_end,
        max_capacity_mw=max_capacity_mw,
    )


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
    """Return yearly degradation rate from linear regression of SoH vs time.

    If SoH is constant (within tolerance) or the regression is ill-posed,
    returns 0 %/yr.

    Args:
        kpi_type_id: KPI type ID used to query SoH data.
        start: Report period start date (data fetched from Jan 1 of that year).
        end: Report period end date.
        project: Project model instance.
        date_col: Column name for dates in the KPI DataFrame.
        soh_col: Column name for SoH values in the KPI DataFrame.
        min_span_days: Minimum date span required to fit a regression.
        atol: Absolute tolerance for detecting a constant SoH series.

    Returns:
        Dict with keys: degradation_rate_pct_per_year, slope_pct_per_year,
        r2, stderr, n_points, span_days.
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


async def get_report_kpi_data(
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
        KPITypeEnum.BESS_STRING_CYCLE_COUNT.value,
        KPITypeEnum.BESS_STRING_SOH.value,
        KPITypeEnum.BESS_STRING_RESTING_SOC_PERCENT.value,
        KPITypeEnum.PROJECT_AVERAGE_SOC_PERCENT.value,
        KPITypeEnum.PROJECT_ENERGY_DISCHARGED.value,
        KPITypeEnum.BESS_PROJECT_ENERGY_CHARGED.value,
        KPITypeEnum.BESS_PROJECT_STRING_SOC_BALANCE_SCORE.value,
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

    project_soc_tags = await crud_get_project_tags_v2(
        sensor_type_ids=[SensorTypeEnum.PROJECT_SOC_PERCENT]
    ).get_async(output_type=OutputType.POLARS, schema=project.name_short)
    tag_id = project_soc_tags["tag_id"][0]

    project_soc_data_instance = DataTimeseries(
        project_db=project_db_sync,
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_POLARS,
        filter_values=project_soc_tags,
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
        kpi_type_id=KPITypeEnum.BESS_STRING_SOH,
        start=start,
        end=end,
        project=project,
    )
    ytd_cycles = crud_get_kpi_data(
        start=start.replace(month=1, day=1),
        end=end,
        project_ids=[project.project_id],
        kpi_type_ids=[KPITypeEnum.BESS_STRING_CYCLE_COUNT.value],
        include_device_data=False,
    )
    ytd_cycles_df = await ytd_cycles.get_async(output_type=OutputType.PANDAS)
    ytd_earliest_date = ytd_cycles_df["date"].min()

    return (
        sums,
        means,
        stats,
        degradation["degradation_rate_pct_per_year"],
        ytd_cycles_df["project_data"].sum(),
        ytd_earliest_date,
    )


async def create_radar_chart(
    *,
    project_id: uuid.UUID,
    start: datetime.date,
    end: datetime.date,
    tps_token: str,
    included_projects: list[str],
) -> tuple[bytes | None, pd.DataFrame | None, str | None]:
    """Create a radar chart for a project.

    Args:
        project_id: The ID of the project.
        start: The start date.
        end: The end date.
        tps_token: The TPS token.
        included_projects: The list of project IDs to include in the radar chart.

    Returns:
        Tuple of (radar chart bytes, dataframe, project name).
    """
    if str(project_id) not in included_projects:
        included_projects.append(str(project_id))
    included_projects_uuid = [uuid.UUID(project_id) for project_id in included_projects]
    kpi_type_ids = [
        KPITypeEnum.BESS_STRING_ENERGY_DISCHARGED,
        KPITypeEnum.BESS_PCS_AVAILABILITY,
        KPITypeEnum.BESS_PCS_MODULE_AVAILABILITY,
        KPITypeEnum.BESS_STRING_AVAILABILITY,
        KPITypeEnum.BESS_BANK_AVAILABILITY,
        KPITypeEnum.BESS_STRING_RESTING_SOC_PERCENT,
        KPITypeEnum.PROJECT_ENERGY_DISCHARGED,
        KPITypeEnum.BESS_PROJECT_STRING_SOC_BALANCE_SCORE,
    ]
    df = await crud_get_kpi_data(
        kpi_type_ids=[kpi_type.value for kpi_type in kpi_type_ids],
        start=start,
        end=end,
        project_ids=included_projects_uuid,
    ).get_async(output_type=OutputType.PANDAS)
    projects = await crud_get_projects(project_ids=included_projects_uuid).get_async(
        output_type=OutputType.PANDAS
    )
    project_lookup = projects.set_index("project_id")

    # Real $ / MWh Delivered and $ / MW Virtual Trades:
    dollars_per_mwh = (
        df[df["kpi_type_id"] == KPITypeEnum.PROJECT_ENERGY_DISCHARGED][
            ["project_id", "project_data"]
        ]
        .groupby("project_id")
        .sum()
        .rename(columns={"project_data": "mwh"})
    )
    virtual_dollars_per_mwh = pd.DataFrame(index=projects["project_id"])
    for i in projects.index:
        project_model = models.Project(**projects.loc[i])
        try:
            tps_element_identifier = await get_tps_element_identifier(
                project=project_model
            )
            tps_data = await get_tps_data(
                project=project_model,
                parent_element_identifier=tps_element_identifier,
                start_dt=start,
                end_dt=end,
                token=tps_token,
            )
            rev_breakdown = tps_data[0]
            virtual_volume = tps_data[3]
            dollars_per_mwh.loc[project_model.project_id, "dollars"] = float(
                rev_breakdown[
                    [
                        "Day-Ahead Energy",
                        "Real-Time Energy",
                        "Misc Charges",
                        "Ancillary Services",
                    ]
                ]
                .sum()
                .sum()
            )
            virtual_dollars_per_mwh.loc[project_model.project_id, "mwh"] = (
                virtual_volume
            )
            virtual_dollars_per_mwh.loc[project_model.project_id, "dollars"] = float(
                rev_breakdown["Virtual Trades"].sum()
            )
        except Exception:  # KeyError or ValueError
            dollars_per_mwh.loc[project_model.project_id, "dollars"] = np.nan

    dollars_per_mwh["dollars_per_mwh"] = (
        dollars_per_mwh["dollars"] / dollars_per_mwh["mwh"]
    )
    dollars_per_mwh.loc[dollars_per_mwh["mwh"] < 1, "dollars_per_mwh"] = np.nan

    virtual_dollars_per_mwh["virtual_dollars_per_mwh"] = (
        virtual_dollars_per_mwh["dollars"] / virtual_dollars_per_mwh["mwh"]
    )

    # Energy Yield (MWh / MW)
    energy_discharged = (
        df[df["kpi_type_id"] == KPITypeEnum.PROJECT_ENERGY_DISCHARGED][
            ["project_id", "project_data"]
        ]
        .groupby("project_id")
        .sum()
    )
    poi_dict = project_lookup["poi"].to_dict()
    energy_discharged = energy_discharged.rename(columns={"project_data": "mwh"})
    energy_discharged["mw"] = energy_discharged.index.map(poi_dict)
    energy_discharged["energy_yield"] = (
        energy_discharged["mwh"] / energy_discharged["mw"]
    )

    # Availability %
    availability = (
        df[
            df["kpi_type_id"].isin(
                [
                    KPITypeEnum.BESS_PCS_AVAILABILITY.value,
                    KPITypeEnum.BESS_PCS_MODULE_AVAILABILITY.value,
                    KPITypeEnum.BESS_STRING_AVAILABILITY.value,
                    KPITypeEnum.BESS_BANK_AVAILABILITY.value,
                ]
            )
        ][["project_id", "project_data"]]
        .groupby("project_id")
        .mean()
        .rename(columns={"project_data": "availability"})
    )

    # Balance of Strings (100% = perfectly balanced)
    balance = df[
        df["kpi_type_id"] == KPITypeEnum.BESS_PROJECT_STRING_SOC_BALANCE_SCORE
    ][["project_id", "project_data"]]
    balance.loc[
        (balance["project_data"] > 1.0) | (balance["project_data"] < 0.0),
        "project_data",
    ] = np.nan
    balance = (
        balance.groupby("project_id")
        .mean()
        .rename(columns={"project_data": "balance_of_strings"})
    )

    # RTE
    rte_dict = await core_get_project_rte(
        project_ids=projects["project_id"].tolist(),
        start=start,
        end=end,
    )
    if rte_dict:
        rte_df = pd.DataFrame.from_dict(
            rte_dict, orient="index", columns=["round_trip_efficiency"]
        )
        rte_df.index.name = "project"
    else:
        rte_df = pd.DataFrame()
    rte_dict_from_modules = await core_get_project_rte_from_modules(
        project_ids=projects["project_id"].tolist(),
        start=start,
        end=end,
    )
    if rte_dict_from_modules:
        rte_df_from_modules = pd.DataFrame.from_dict(
            rte_dict_from_modules, orient="index", columns=["round_trip_efficiency"]
        )
        rte_df_from_modules.index.name = "project"
    else:
        rte_df_from_modules = pd.DataFrame()
    rte_combined = (
        rte_df.combine_first(rte_df_from_modules)
        if not rte_df.empty
        else rte_df_from_modules
    )

    # Combine KPIs
    raw_metrics = pd.concat(
        [
            energy_discharged["energy_yield"],
            availability["availability"],
            balance["balance_of_strings"],
            dollars_per_mwh["dollars_per_mwh"],
            virtual_dollars_per_mwh["virtual_dollars_per_mwh"],
            rte_combined,
        ],
        axis=1,
    )

    numeric_cols = raw_metrics.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        raise ValueError("No numeric KPI columns available for radar chart.")

    normalized = raw_metrics.copy()
    mean_values = normalized.loc[:, numeric_cols].mean(numeric_only=True)
    normalized.loc["mean", numeric_cols] = mean_values
    normalized.loc[:, numeric_cols] = (
        normalized.loc[:, numeric_cols].div(mean_values) * 100.0
    )
    normalized = normalized.drop(index="mean")

    if project_id not in normalized.index:
        raise KeyError(f"Project '{project_id}' is not present in aggregated KPI data.")

    proj_values = normalized.loc[project_id, numeric_cols].astype(float).fillna(100.0)  # type: ignore
    display_names = {
        "energy_yield": "Energy Yield (MWh/MW)",
        "availability": "Availability (%)",
        "balance_of_strings": "Balance of Strings",
        "dollars_per_mwh": "Real $ / MWh Delivered",
        "virtual_dollars_per_mwh": "Virtual $ / MWh Volume",
        "round_trip_efficiency": "RTE (%)",
    }
    polar_theta_label_overrides = {
        "virtual_dollars_per_mwh": "Virtual $ / MWh<br>Volume",
    }
    theta_labels = [
        polar_theta_label_overrides.get(
            column,
            display_names.get(column, column.replace("_", " ").title()),
        )
        for column in numeric_cols
    ]
    closed_values = proj_values.tolist() + [proj_values.iloc[0]]
    closed_theta = theta_labels + [theta_labels[0]]
    reference_values = [100.0] * len(closed_theta)

    project_names = project_lookup["name_long"].to_dict()
    project_name = project_names.get(project_id, str(project_id))

    raw_metrics = raw_metrics.rename(columns=display_names)
    raw_metrics.index = raw_metrics.index.map(
        lambda idx: project_names.get(idx, str(idx))
    )
    portfolio_mean = raw_metrics.mean(numeric_only=True)
    portfolio_mean.name = "Portfolio Mean"
    raw_metrics = pd.concat([raw_metrics, portfolio_mean.to_frame().T], axis=0)

    ordered_projects = [
        project_name,
        *(
            idx
            for idx in raw_metrics.index
            if idx not in {project_name, "Portfolio Mean"}
        ),
        "Portfolio Mean",
    ]
    # Deduplicate while preserving order
    seen: set[str] = set()
    ordered_unique: list[str] = []
    for idx in ordered_projects:
        if idx in raw_metrics.index and idx not in seen:
            ordered_unique.append(idx)
            seen.add(idx)
    raw_metrics = raw_metrics.loc[ordered_unique]

    max_value = max(max(closed_values), 100.0)
    radial_max_computed = max(120.0, float(np.ceil(max_value / 10.0) * 10.0))
    radial_cap = 300.0
    capped_at_radial_max = radial_max_computed > radial_cap
    radial_max = radial_cap if capped_at_radial_max else radial_max_computed
    plot_closed_values = (
        [min(v, radial_max) for v in closed_values]
        if capped_at_radial_max
        else closed_values
    )
    tickvals = list(np.arange(0, radial_max + 1, 20.0))

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=reference_values,
            theta=closed_theta,
            name="Portfolio Mean (100)",
            line=dict(color="#1f77b4", dash="dash"),
            fill="none",
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=plot_closed_values,
            theta=closed_theta,
            name=str(project_name),
            fill="toself",
            fillcolor="rgba(255, 127, 14, 0.2)",
            line=dict(width=2, color="#ff7f0e"),
            marker=dict(size=6),
        )
    )
    if capped_at_radial_max:
        overflow_theta: list[str] = []
        overflow_r: list[float] = []
        overflow_text: list[str] = []
        for i, _col in enumerate(numeric_cols):
            v = float(proj_values.iloc[i])
            if v > radial_cap:
                overflow_theta.append(theta_labels[i])
                overflow_r.append(radial_max * 0.94)
                overflow_text.append(f"{v:.0f}%")
        if overflow_text:
            fig.add_trace(
                go.Scatterpolar(
                    r=overflow_r,
                    theta=overflow_theta,
                    text=overflow_text,
                    mode="text",
                    textposition="top center",
                    textfont=dict(size=11, color="#36454F"),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(range=[0, radial_max], tickvals=tickvals),
            angularaxis=dict(rotation=90, direction="clockwise"),
        ),
        legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
        margin=dict(t=80, b=80, l=40, r=40),
        width=700,
        height=700,
    )

    image_bytes = bytes(fig.to_image(format="png", width=700, height=700, scale=2))
    return image_bytes, raw_metrics, project_name


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

    def _to_naive_timestamp(value):  # no-star-syntax
        """Strip timezone info from a timestamp, returning a naive Timestamp.

        Args:
            value: Datetime-like value to convert to a naive Timestamp.
        """
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
        db=project_db, device_type_ids=[DeviceTypeEnum.BESS_PCS_MODULE]
    )
    total_ac_power_capacity = float(sum((x.capacity_ac or 0.0) for x in all_devices))
    total_energy_capacity = (
        total_ac_power_capacity * (end - start).total_seconds() / 3600 / 1_000
    )

    losses_dict: dict[str, float] = (
        {
            str(name): float(loss)
            for name, loss in loss_by_failure_mode_id.set_index(
                "failure_mode_name_long"
            )["capacity_loss_mwh"]
            .sort_values(ascending=False)
            .mul(-1.0)
            .items()
        }
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
    frac_covered = covered_fraction_by_any_event(events=event_df, start=start, end=end)
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
    """Build event table.

    Args:
        project_db: Async database session for the project database.
        top_ten_losses: DataFrame of the top capacity-loss events to display.
    """
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
    total_availability: float | None,
    market_availability: float | None,
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
        market_availability: Availability derived from market outage tickets.
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
        "total_energy_charged": 0,
        "capacity_weighted_availability": 0.98,
        "market_availability": 0.98,
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
            "Total Energy Discharged",
            "Total Energy Charged",
            "Capacity-Weighted Availability",
            "Market Availability",
            "Degradation Rate",
            "Forecast Accuracy",
        ],
        columns=["This Month", "Expected", "Delta"],
    )

    executive_summary_df.loc["Total Revenue", "This Month"] = rev_breakdown_df[
        "Net Profit"
    ].sum()
    executive_summary_df.loc["Total Revenue", "Expected"] = defaults["total_revenue"]
    executive_summary_df.loc["Total Energy Discharged", "This Month"] = other_tps_data[
        "Total Energy Discharged"
    ]
    executive_summary_df.loc["Total Energy Discharged", "Expected"] = defaults[
        "total_energy_delivered"
    ]
    executive_summary_df.loc["Total Energy Charged", "This Month"] = other_tps_data[
        "Total Energy Charged"
    ]
    executive_summary_df.loc["Total Energy Charged", "Expected"] = defaults[
        "total_energy_charged"
    ]
    executive_summary_df.loc["Capacity-Weighted Availability", "This Month"] = (
        total_availability
    )
    executive_summary_df.loc["Capacity-Weighted Availability", "Expected"] = defaults[
        "capacity_weighted_availability"
    ]
    executive_summary_df.loc["Market Availability", "This Month"] = market_availability
    executive_summary_df.loc["Market Availability", "Expected"] = defaults[
        "market_availability"
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
    """Compare the strategies to the perfect foresight strategy.

    Args:
        strategies: List of BESS monthly report strategies to evaluate.
    """
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
        contract_kpis["kpi_type_id"]
        == KPITypeEnum.BESS_PROJECT_MINIMUM_USABLE_ENERGY_CAPACITY
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
        current_aniv_ts = cast(pd.Timestamp, current_aniv)
        year_slice = contract_uec.loc[current_aniv_ts:].iloc[:2]

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

    local_path = Path(local_filename)
    temp_dir_path = local_path.parent
    temp_dir = str(temp_dir_path)
    try:
        await asyncio.to_thread(_upload)
    finally:
        if await asyncio.to_thread(local_path.exists):
            try:
                await asyncio.to_thread(os.remove, local_filename)
            except OSError:
                pass
        if await asyncio.to_thread(temp_dir_path.is_dir) and temp_dir.startswith(
            tempfile.gettempdir()
        ):
            await asyncio.to_thread(shutil.rmtree, temp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------


async def generate_eec_bess_monthly_report(
    *,
    project: models.Project,
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

    (
        rev_breakdown_df,
        generation_hourly,
        consumption_hourly,
        _,
    ) = await get_tps_data(
        project=project,
        parent_element_identifier=tps_element_identifier,
        start_dt=req_start,
        end_dt=req_end,
        token=tps_token,
    )

    rev_breakdown_by_type_bytes = await generate_revenue_breakdown_chart(
        rev_breakdown_df=rev_breakdown_df,
    )

    monthly_tbx = await get_tbx(
        project=project,
        start=pd.Timestamp(req_start),
        end=pd.Timestamp(req_end),
        token=tps_token,
        total_profit=rev_breakdown_df["Net Profit"].sum(),
    )
    try:
        (
            radar_chart_bytes,
            radar_table_df,
            selected_project_name,
        ) = await create_radar_chart(
            project_id=project.project_id,
            start=req_start,
            end=req_end,
            tps_token=tps_token,
            included_projects=request.included_projects,
        )
    except Exception:  # pragma: no cover - logging fallback
        logger.exception(
            "Failed to generate radar chart for project_id=%s", project.project_id
        )
        radar_chart_bytes = None
        radar_table_df = None
        selected_project_name = None
    # Pass real PNG bytes for rev_breakdown_by_type / bess_pcs_availability
    # when available.
    (
        kpi_sums,
        kpi_means,
        soc_stats,
        degradation_rate,
        ytd_cycles,
        ytd_earliest_date,
    ) = await get_report_kpi_data(
        project=project,
        project_db_sync=project_db_sync,
        start=req_start,
        end=req_end,
    )
    other_tps_data = {
        "Total Energy Discharged": kpi_sums.loc[
            KPITypeEnum.PROJECT_ENERGY_DISCHARGED.value, "project_data"
        ],
        "Total Energy Charged": kpi_sums.loc[
            KPITypeEnum.BESS_PROJECT_ENERGY_CHARGED.value, "project_data"
        ],
    }
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
    else:
        total_availability = None

    market_availability = await get_market_availability(
        project=project,
        token=tps_token,
        start=req_start,
        end=req_end,
    )
    req_days = (req_end - req_start).total_seconds() / 60 / 60 / 24
    expected_energy = project.capacity_bess_energy_bol_dc * req_days
    expected_values = {
        "total_energy_delivered": expected_energy,
        "total_energy_charged": expected_energy,
    }

    executive_summary_df = await generate_executive_summary(
        other_tps_data=other_tps_data,
        rev_breakdown_df=rev_breakdown_df,
        expected_values=expected_values,
        total_availability=total_availability,
        market_availability=market_availability,
        degradation_rate=degradation_rate,
        deg_rate_expected=deg_rate,
        request=request,
    )
    kpi_expected_values = {
        "monthly_cycles": (req_end - max(req_start, ytd_earliest_date)).days,
        "ytd_cycles": (req_end - ytd_earliest_date).days,
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
        radar_table_df=radar_table_df,
        radar_selected_project=selected_project_name,
        radar_chart_bytes=radar_chart_bytes,
        ytd_cycles=ytd_cycles,
    )
    await upload_to_aws(local_filename=filename)


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


type TimestampLike = datetime.datetime | datetime.date | pd.Timestamp


def _ensure_utc(*, ts: pd.Timestamp) -> pd.Timestamp:
    """Return the timestamp converted to or localized in UTC.

    Args:
        ts: Timestamp to normalize.
    """
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
    """Return seconds in [start, end) covered by at least one event.

    Null end times are treated as ``ongoing_end`` if provided, otherwise
    ``end``. Intervals are half-open: [event_start, event_end).

    Args:
        events: DataFrame containing event intervals.
        start: Window start (inclusive).
        end: Window end (exclusive).
        time_start_col: Column name for event start timestamps.
        time_end_col: Column name for event end timestamps (may be null).
        ongoing_end: Fallback end for null-end (ongoing) events.
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
        start_ts = _ensure_utc(ts=start_ts)
        end_ts = _ensure_utc(ts=end_ts)
        if ongoing_end_ts is not None:
            ongoing_end_ts = _ensure_utc(ts=ongoing_end_ts)
    elif start_ts.tz is not None or end_ts.tz is not None:
        time_start_series = time_start_series.dt.tz_localize("UTC")
        time_end_series = time_end_series.dt.tz_localize("UTC")
        start_ts = _ensure_utc(ts=start_ts)
        end_ts = _ensure_utc(ts=end_ts)
        if ongoing_end_ts is not None:
            ongoing_end_ts = _ensure_utc(ts=ongoing_end_ts)

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
    *,
    events: pd.DataFrame,
    start: TimestampLike,
    end: TimestampLike,
    time_start_col: str = "time_start",
    time_end_col: str = "time_end",
    ongoing_end: TimestampLike | None = None,
) -> float:
    """Fraction of [start,end) covered by at least one event.

    Args:
        events: DataFrame containing event intervals.
        start: Window start (inclusive).
        end: Window end (exclusive).
        time_start_col: Column name for event start timestamps.
        time_end_col: Column name for event end timestamps (may be null).
        ongoing_end: Fallback end for null-end (ongoing) events.
    """
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
