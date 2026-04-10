"""Load device and tag rows from CSV files (e.g. Google Sheets export)."""

import csv
from pathlib import Path

from inspectui.core.models import DeviceInfo, TagInfo

_DEVICE_REQUIRED: frozenset[str] = frozenset(
    {
        "device_id",
        "device_type_id",
        "name_short",
        "name_long",
        "parent_device_id",
        "capacity_dc",
        "capacity_ac",
    }
)

_TAG_REQUIRED: frozenset[str] = frozenset(
    {
        "tag_id",
        "device_id",
        "sensor_type_id",
        "name_scada",
    }
)


def _strip_cell(raw: str | None) -> str:
    if raw is None:
        return ""
    return raw.strip()


def _parse_optional_int(*, cell: str, column: str, row_num: int) -> int | None:
    s = _strip_cell(cell)
    if not s:
        return None
    try:
        return int(s)
    except ValueError as e:
        raise ValueError(f"Row {row_num}: invalid integer for {column}: {s!r}") from e


def _parse_required_int(*, cell: str, column: str, row_num: int) -> int:
    s = _strip_cell(cell)
    if not s:
        raise ValueError(f"Row {row_num}: missing required {column}")
    try:
        return int(s)
    except ValueError as e:
        raise ValueError(f"Row {row_num}: invalid integer for {column}: {s!r}") from e


def _parse_optional_float(*, cell: str, column: str, row_num: int) -> float | None:
    s = _strip_cell(cell)
    if not s:
        return None
    try:
        return float(s)
    except ValueError as e:
        raise ValueError(f"Row {row_num}: invalid float for {column}: {s!r}") from e


def _parse_optional_str(*, cell: str) -> str | None:
    s = _strip_cell(cell)
    return s or None


def _parse_in_tsdb(*, cell: str, row_num: int) -> bool:
    s = _strip_cell(cell).lower()
    if not s:
        raise ValueError(f"Row {row_num}: in_tsdb is required")
    if s in ("true", "t", "yes", "y", "1"):
        return True
    if s in ("false", "f", "no", "n", "0"):
        return False
    raise ValueError(f"Row {row_num}: invalid in_tsdb (use true/false or 0/1): {s!r}")


def _validate_headers(
    *,
    found: list[str],
    required: frozenset[str],
    label: str,
) -> None:
    """Require DB column names; extra columns (e.g. from Sheets) are ignored."""
    found_set = frozenset(found)
    missing = required - found_set
    if missing:
        raise ValueError(f"{label}: missing columns: {', '.join(sorted(missing))}")


def _normalize_row_keys(row: dict[str, str | None]) -> dict[str, str]:
    """Strip header names and cell values for robust DictReader rows."""
    out: dict[str, str] = {}
    for k, v in row.items():
        key = _strip_cell(k)
        if not key:
            continue
        out[key] = v
    return out


def load_devices_csv(*, path: Path) -> list[DeviceInfo]:
    """Load devices from a CSV with required DB columns.

    Extra columns (e.g. helper columns from spreadsheets) are ignored.

    Args:
        path: Path to devices.csv.

    Returns:
        Rows as DeviceInfo, sorted by device_id.

    Raises:
        ValueError: Missing file, missing required columns, or bad cell value.
        OSError: File cannot be read.
    """
    if not path.is_file():
        raise ValueError(f"Devices CSV not found: {path}")

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("Devices CSV has no header row")
        headers = [h.strip() for h in reader.fieldnames if h is not None]
        _validate_headers(found=headers, required=_DEVICE_REQUIRED, label=path.name)

        rows: list[DeviceInfo] = []
        for row_num, raw in enumerate(reader, start=2):
            row = _normalize_row_keys(raw)
            if not any(_strip_cell(v) for v in row.values()):
                continue
            dmid: int | None = None
            if "device_model_id" in row:
                dmid = _parse_optional_int(
                    cell=row["device_model_id"],
                    column="device_model_id",
                    row_num=row_num,
                )
            rows.append(
                DeviceInfo(
                    device_id=_parse_required_int(
                        cell=row["device_id"],
                        column="device_id",
                        row_num=row_num,
                    ),
                    device_type_id=_parse_required_int(
                        cell=row["device_type_id"],
                        column="device_type_id",
                        row_num=row_num,
                    ),
                    name_short=_parse_optional_str(cell=row["name_short"]),
                    name_long=_parse_optional_str(cell=row["name_long"]),
                    parent_device_id=_parse_optional_int(
                        cell=row["parent_device_id"],
                        column="parent_device_id",
                        row_num=row_num,
                    ),
                    capacity_dc=_parse_optional_float(
                        cell=row["capacity_dc"],
                        column="capacity_dc",
                        row_num=row_num,
                    ),
                    capacity_ac=_parse_optional_float(
                        cell=row["capacity_ac"],
                        column="capacity_ac",
                        row_num=row_num,
                    ),
                    device_model_id=dmid,
                )
            )

    rows.sort(key=lambda d: d.device_id)
    return rows


def load_tags_csv(*, path: Path) -> list[TagInfo]:
    """Load tags from a CSV with required DB columns.

    Extra columns are ignored.

    Args:
        path: Path to tags.csv.

    Returns:
        Rows as TagInfo, sorted by tag_id.

    Raises:
        ValueError: Missing file, missing required columns, or bad cell value.
        OSError: File cannot be read.
    """
    if not path.is_file():
        raise ValueError(f"Tags CSV not found: {path}")

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("Tags CSV has no header row")
        headers = [h.strip() for h in reader.fieldnames if h is not None]
        _validate_headers(found=headers, required=_TAG_REQUIRED, label=path.name)

        rows: list[TagInfo] = []
        for row_num, raw in enumerate(reader, start=2):
            row = _normalize_row_keys(raw)
            if not any(_strip_cell(v) for v in row.values()):
                continue
            name_scada_raw = _strip_cell(row["name_scada"])
            if not name_scada_raw:
                raise ValueError(f"Row {row_num}: name_scada is required")
            rows.append(
                TagInfo(
                    tag_id=_parse_required_int(
                        cell=row["tag_id"],
                        column="tag_id",
                        row_num=row_num,
                    ),
                    device_id=_parse_required_int(
                        cell=row["device_id"],
                        column="device_id",
                        row_num=row_num,
                    ),
                    sensor_type_id=_parse_optional_int(
                        cell=row["sensor_type_id"],
                        column="sensor_type_id",
                        row_num=row_num,
                    ),
                    data_type_id=_parse_optional_int(
                        cell=row["data_type_id"],
                        column="data_type_id",
                        row_num=row_num,
                    ),
                    name_short=_parse_optional_str(cell=row["name_short"]),
                    name_long=_parse_optional_str(cell=row["name_long"]),
                    name_scada=name_scada_raw,
                    in_tsdb=_parse_in_tsdb(cell=row["in_tsdb"], row_num=row_num),
                )
            )

    rows.sort(key=lambda t: t.tag_id)
    return rows


def project_devices_csv_path(*, root: Path, name_short: str) -> Path:
    """Path to the devices CSV for a project in a single directory.

    Filename: ``{name_short} - devices.csv`` (e.g. under ``~/Downloads`` on macOS).
    Tags are not loaded from CSV in the TUI workflow; use the database for tags.

    Args:
        root: Directory containing the CSV (typically ``~/Downloads``).
        name_short: Project short name.

    Returns:
        Path to the devices file.
    """
    return root / f"{name_short} - devices.csv"


def default_csv_directory() -> Path:
    """Default folder for CSV imports on macOS: ``~/Downloads``."""
    return (Path.home() / "Downloads").expanduser().resolve()
