import math
from typing import Any, cast

import pandas as pd
from core.db_query import OutputType
from core.enumerations import DeviceTypeEnum
from fastapi import HTTPException, status
from shapely.errors import GEOSException
from shapely.wkb import loads as wkb_loads
from shapely.wkt import loads as wkt_loads
from sqlalchemy.orm import Session

import core
from app import utils
from app.domain.eem.google_sheet.read.s01_read_gsheet import (
    _build_google_sheets_service,
    _column_index_to_letter,
)

SHEET_NAME = "Input"
INVERTER_COLUMN = "PCS Number"
MET_STATION_COLUMN = "Met Name"


def _normalize_cell_value(*, value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def _point_to_lon_lat(*, point: Any) -> tuple[float, float] | None:
    if point is None:
        return None

    try:
        if isinstance(point, memoryview):
            geometry = wkb_loads(bytes(point))
        elif isinstance(point, (bytes, bytearray)):
            geometry = wkb_loads(bytes(point))
        elif isinstance(point, str):
            point_text = point.strip()
            if not point_text:
                return None
            if point_text.upper().startswith("POINT"):
                geometry = wkt_loads(point_text)
            else:
                geometry = wkb_loads(bytes.fromhex(point_text))
        elif hasattr(point, "data"):
            geometry = wkb_loads(bytes(point.data))
        else:
            return None
    except (GEOSException, TypeError, ValueError):
        return None

    return float(geometry.x), float(geometry.y)


def _haversine_distance_meters(
    *,
    first_lon_lat: tuple[float, float],
    second_lon_lat: tuple[float, float],
) -> float:
    first_lon, first_lat = first_lon_lat
    second_lon, second_lat = second_lon_lat
    earth_radius_meters = 6_371_000

    first_lat_rad = math.radians(first_lat)
    second_lat_rad = math.radians(second_lat)
    lat_delta = math.radians(second_lat - first_lat)
    lon_delta = math.radians(second_lon - first_lon)

    a = (
        math.sin(lat_delta / 2) ** 2
        + math.cos(first_lat_rad)
        * math.cos(second_lat_rad)
        * math.sin(lon_delta / 2) ** 2
    )
    return 2 * earth_radius_meters * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def _get_nearest_met_names_by_inverter_name(
    *,
    project_db: Session,
) -> dict[str, str]:
    project_schema = utils.get_project_schema(project_db=project_db)
    devices = await core.crud.project.devices.get_project_devices(
        device_type_ids=[
            DeviceTypeEnum.PV_INVERTER,
            DeviceTypeEnum.MET_STATION,
        ],
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    if not isinstance(devices, pd.DataFrame) or devices.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No PV inverter or met station devices found for this project.",
        )

    inverters = devices[devices["device_type_id"] == DeviceTypeEnum.PV_INVERTER]
    met_stations = devices[devices["device_type_id"] == DeviceTypeEnum.MET_STATION]

    if inverters.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No PV inverter devices found for this project.",
        )
    if met_stations.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No met station devices found for this project.",
        )

    met_station_points: list[tuple[str, tuple[float, float]]] = []
    for _, met_station in met_stations.iterrows():
        met_name = _normalize_cell_value(value=met_station.get("name_short"))
        met_point = _point_to_lon_lat(point=met_station.get("point"))
        if met_name and met_point is not None:
            met_station_points.append((met_name, met_point))

    if not met_station_points:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Met station devices need name_short and point values.",
        )

    nearest_met_name_by_inverter_name: dict[str, str] = {}
    for _, inverter in inverters.iterrows():
        inverter_name = _normalize_cell_value(value=inverter.get("name_long"))
        inverter_point = _point_to_lon_lat(point=inverter.get("point"))
        if not inverter_name:
            continue
        if inverter_point is None:
            continue

        nearest_met_name, _ = min(
            (
                (
                    met_name,
                    _haversine_distance_meters(
                        first_lon_lat=inverter_point,
                        second_lon_lat=met_point,
                    ),
                )
                for met_name, met_point in met_station_points
            ),
            key=lambda item: item[1],
        )
        nearest_met_name_by_inverter_name[inverter_name] = nearest_met_name

    if not nearest_met_name_by_inverter_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PV inverter devices need name_long and point values.",
        )

    return nearest_met_name_by_inverter_name


def _get_sheet_rows(*, service: Any, spreadsheet_id: str) -> list[list[str]]:
    spreadsheets_api = service.spreadsheets()
    values_api = spreadsheets_api.values()
    get_values = values_api.get
    google_request = get_values(
        spreadsheetId=spreadsheet_id,
        range=SHEET_NAME,
    )
    values = google_request.execute().get("values", [])
    return cast(list[list[str]], values)


def _update_met_name_column(
    *,
    service: Any,
    spreadsheet_id: str,
    met_column_index: int,
    rows: list[list[str]],
) -> None:
    met_column_letter = _column_index_to_letter(index=met_column_index)
    update_range = (
        f"{SHEET_NAME}!{met_column_letter}2:{met_column_letter}{len(rows) + 1}"
    )
    body = {"values": [[row[met_column_index]] for row in rows]}
    spreadsheets_api = service.spreadsheets()
    values_api = spreadsheets_api.values()
    update_values = values_api.update
    google_request = update_values(
        spreadsheetId=spreadsheet_id,
        range=update_range,
        valueInputOption="USER_ENTERED",
        body=body,
    )
    google_request.execute()


async def map_inverters_to_met_stations(
    *,
    project_db: Session,
    spreadsheet_id: str,
) -> dict[str, int]:
    """Write nearest met station names into the Google Sheet input rows.

    Args:
        project_db: Project database session used to read device locations.
        spreadsheet_id: Google Sheet ID to update.
    """
    nearest_met_name_by_inverter_name = await _get_nearest_met_names_by_inverter_name(
        project_db=project_db,
    )
    service = _build_google_sheets_service()
    values = _get_sheet_rows(service=service, spreadsheet_id=spreadsheet_id)

    if not values or not values[0]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No header row found in the Google Sheet Input tab.",
        )

    headers = values[0]
    try:
        inverter_column_index = headers.index(INVERTER_COLUMN)
        met_column_index = headers.index(MET_STATION_COLUMN)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Google Sheet Input tab must include {INVERTER_COLUMN!r} and "
                f"{MET_STATION_COLUMN!r} columns."
            ),
        ) from error

    rows = [list(row) for row in values[1:]]
    rows_updated = 0
    matched_inverter_names: set[str] = set()
    missing_inverter_names: set[str] = set()
    for row in rows:
        while len(row) < len(headers):
            row.append("")

        inverter_name = _normalize_cell_value(value=row[inverter_column_index])
        if not inverter_name:
            continue

        met_name = nearest_met_name_by_inverter_name.get(inverter_name)
        if met_name is None:
            missing_inverter_names.add(inverter_name)
            continue

        matched_inverter_names.add(inverter_name)
        if row[met_column_index] != met_name:
            row[met_column_index] = met_name
            rows_updated += 1

    if missing_inverter_names:
        missing_names = ", ".join(sorted(missing_inverter_names)[:10])
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Some PCS Number values do not match PV inverter devices "
                "with point values in project.devices: "
                f"{missing_names}"
            ),
        )

    if rows:
        _update_met_name_column(
            service=service,
            spreadsheet_id=spreadsheet_id,
            met_column_index=met_column_index,
            rows=rows,
        )

    return {
        "rows_updated": rows_updated,
        "inverters_mapped": len(matched_inverter_names),
        "met_stations_available": len(set(nearest_met_name_by_inverter_name.values())),
    }
