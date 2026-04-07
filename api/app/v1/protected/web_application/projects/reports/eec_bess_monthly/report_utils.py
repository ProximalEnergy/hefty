"""Shared utilities for PDF report generation.

This module contains reusable functions for formatting, calculations,
table creation, and image handling used across report generation modules.
"""

import base64
import math
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.platypus import Image, TableStyle

# ---------------------------------------------------------------------------
# Formatting Functions
# ---------------------------------------------------------------------------


def format_dollar_value(  # nosemgrep: python-enforce-keyword-only-args
    value: float,
    decimals: int = 2,
) -> str:
    """Format a numeric value as currency.

    Args:
        value: The numeric value to format.
        decimals: Number of decimal places (default: 2).

    Returns:
        Formatted string like "$1,234.56".
    """
    return f"${value:,.{decimals}f}"


def format_energy_value(  # nosemgrep: python-enforce-keyword-only-args
    value: float,
    decimals: int = 2,
) -> str:
    """Format a numeric value as energy in MWh.

    Args:
        value: The numeric value to format.
        decimals: Number of decimal places (default: 2).

    Returns:
        Formatted string like "1,234.56 MWh".
    """
    return f"{value:,.{decimals}f} MWh"


def format_percentage_value(  # nosemgrep: python-enforce-keyword-only-args
    value: float,
    decimals: int = 2,
) -> str:
    """Format a numeric value as percentage.

    Args:
        value: The numeric value (0.95 for 95%).
        decimals: Number of decimal places (default: 2).

    Returns:
        Formatted string like "95.00%".
    """
    return f"{(value * 100):.{decimals}f}%"


def format_dollar_per_kw_value(  # nosemgrep: python-enforce-keyword-only-args
    value: float,
    decimals: int = 2,
) -> str:
    """Format a numeric value as currency per kW.

    Args:
        value: The numeric value to format.
        decimals: Number of decimal places (default: 2).

    Returns:
        Formatted string like "1,234.56 $/kW".
    """
    return f"{value:,.{decimals}f} $/kW"


def format_percentage_per_year(  # nosemgrep: python-enforce-keyword-only-args
    value: float,
    decimals: int = 2,
) -> str:
    """Format a numeric value as percentage per year.

    Args:
        value: The numeric value (0.0035 for 0.35%/yr).
        decimals: Number of decimal places (default: 2).

    Returns:
        Formatted string like "0.35%/yr".
    """
    return f"{(value * 100):.{decimals}f}%/yr"


def format_change_text(  # nosemgrep: python-enforce-keyword-only-args
    value: str,
) -> str:
    """Format change indicator text with color.

    Args:
        value: String starting with "▲" or "▼" or other.

    Returns:
        HTML-formatted string with color tags.
    """
    if value.startswith("▲"):
        return f"<font color='darkgreen'>{value}</font>"
    elif value.startswith("▼"):
        return f"<font color='red'>{value}</font>"
    else:
        return value


def format_change_text_reversed(  # nosemgrep: python-enforce-keyword-only-args
    value: str,
) -> str:
    """Format change indicator text with color.

    Args:
        value: String starting with "▲" or "▼" or other.

    Returns:
        HTML-formatted string with color tags.
    """
    if value.startswith("▲"):
        return f"<font color='red'>{value}</font>"
    elif value.startswith("▼"):
        return f"<font color='darkgreen'>{value}</font>"
    else:
        return value


# ---------------------------------------------------------------------------
# Calculation Functions
# ---------------------------------------------------------------------------


def calc_delta_percentage(
    *,
    actual: float | None,
    expected: float | None,
    format_as_change: bool = False,
) -> str:
    """Calculate percentage delta between actual and expected values.

    Args:
        actual: The actual value.
        expected: The expected value.
        format_as_change: If True, format with ▲/▼ indicators.

    Returns:
        Formatted delta string like "+5.23%" or "▲+5.23%".
    """
    if (
        actual is None
        or expected is None
        or math.isnan(actual)
        or math.isnan(expected)
        or expected == 0
    ):
        return "—"
    val = (actual - expected) / expected * 100
    if val > 0:
        prefix = "▲+" if format_as_change else "+"
        return f"{prefix}{abs(val):.2f}%"
    elif val < 0:
        prefix = "▼-" if format_as_change else "-"
        return f"{prefix}{abs(val):.2f}%"
    else:
        return "—"


def calc_delta_value(*, actual: float, expected: float) -> float:
    """Calculate raw delta value (actual - expected).

    Args:
        actual: The actual value.
        expected: The expected value.

    Returns:
        Delta value.
    """
    return actual - expected


# ---------------------------------------------------------------------------
# Image Handling
# ---------------------------------------------------------------------------


def load_image_from_source(  # nosemgrep: python-enforce-keyword-only-args
    img_source: str | bytes | BytesIO,
) -> Image:
    """Load an Image from various source types.

    Args:
        img_source: File path (str), bytes, or BytesIO object.

    Returns:
        ReportLab Image object.
    """
    if isinstance(img_source, str):
        return Image(img_source)
    elif isinstance(img_source, bytes):
        return Image(BytesIO(img_source))
    else:  # Already BytesIO
        return Image(img_source)


def img_fit_by_width(
    *, img: Image, target_w: float, max_h: float | None = None
) -> Image:
    """Scale an Image to fit a target width, optional cap on height.

    Preserves aspect ratio.

    Args:
        img: ReportLab Image object.
        target_w: Target width in points.
        max_h: Optional maximum height in points.

    Returns:
        Modified Image object with adjusted dimensions.
    """
    if max_h is None:
        scale = target_w / img.imageWidth
    else:
        scale = min(target_w / img.imageWidth, max_h / img.imageHeight)
    img.drawWidth = img.imageWidth * scale
    img.drawHeight = img.imageHeight * scale
    return img


# ---------------------------------------------------------------------------
# Table Styling
# ---------------------------------------------------------------------------


def tstyle_compact_grid() -> TableStyle:
    """Standard compact table cell padding & valign.

    Returns:
        TableStyle with minimal padding and middle vertical alignment.
    """
    return TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 1),
            ("RIGHTPADDING", (0, 0), (-1, -1), 1),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]
    )


def tstyle_gridded_table(
    *,
    header_bg: Any = colors.lightgrey,
    row_bg_alt: Any = None,
) -> TableStyle:
    """Table style with grid lines and optional alternating row colors.

    Args:
        header_bg: Background color for header row.
        row_bg_alt: Optional alternating row background color.

    Returns:
        TableStyle with grid, box, and optional row backgrounds.
    """
    style_rules = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    if header_bg:
        style_rules.append(("BACKGROUND", (0, 0), (-1, 0), header_bg))
    if row_bg_alt:
        style_rules.append(
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [colors.white, row_bg_alt],
            )
        )
    return TableStyle(style_rules)


# ---------------------------------------------------------------------------
# Placeholder Images
# ---------------------------------------------------------------------------


# A tiny, valid 1x1 PNG. Use this anywhere we need PNG bytes but the real
# chart hasn't been generated yet.
PLACEHOLDER_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIW2Ng"
    "YGD4DwABBAEAeFf6WQAAAABJRU5ErkJggg=="
)
